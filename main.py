import os
import json
import io

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Cấu Hình ──────────────────────────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID", "1512303397120901191"))
CONFIG_FILE = "welcome_config.json"

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")

ACCENT_COLOUR = discord.Colour.from_rgb(255, 165, 0)

# Mặc định cho khối chào mừng thứ 2
DEFAULT_EMBED2_TITLE = "🐾 {ping}Một Chú Mèo Mới Đã Xuất Hiện!"
DEFAULT_EMBED2_DESC = (
    "Xin Chào Mừng **{member}** Đến Với **{guild}**! 😻\n"
    "Rất Vui Vì Bạn Đã Ghé Thăm Ngôi Nhà Của Những Chú Mèo Đáng Yêu.\n\n"
    "{ping_message}\n\n"
    "Chúc Bạn Có Thật Nhiều Khoảnh Khắc Vui Vẻ Và Kết Bạn Thật Nhiều Nhé! 🎉"
)
DEFAULT_EMBED2_FOOTER = "🐱 {guild} • Hãy Cùng Nhau Vui Chơi Thật Vui Nhé!"

# ── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── Hàm Hỗ Trợ Lưu Trữ Cấu Hình ──────────────────────────────────────────────
def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_guild_config(guild_id: int) -> dict:
    config = load_config()
    return config.get(str(guild_id), {})

def update_guild_config(guild_id: int, **kwargs) -> None:
    config = load_config()
    guild_cfg = config.get(str(guild_id), {})
    for key, value in kwargs.items():
        if value is not None:
            guild_cfg[key] = value
    config[str(guild_id)] = guild_cfg
    save_config(config)

# ── Kiểm Tra Owner ────────────────────────────────────────────────────────────
async def owner_only(interaction: discord.Interaction) -> bool:
    if interaction.user.id != OWNER_ID:
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay("## ❌ Từ Chối Quyền"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay("⚠️ Chỉ **Chủ Bot** Mới Có Thể Sử Dụng Lệnh Này!")
        )
        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)
        return False
    return True

# ── Tạo Ảnh Welcome ──────────────────────────────────────────────────────────
_FONT_CACHE: dict = {}

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    cache_key = (path, size)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    try:
        font = ImageFont.truetype(path, size)
        _FONT_CACHE[cache_key] = font
        return font
    except:
        # Fallback: dùng font mặc định nếu không tìm thấy
        font = ImageFont.load_default()
        _FONT_CACHE[cache_key] = font
        return font

def generate_welcome_card(avatar_bytes: bytes, username: str, member_number: int,
                           guild_name: str) -> io.BytesIO:
    W, H = 900, 300
    RADIUS = 34
    TOP_LEFT = (255, 165, 0, 50)
    BOTTOM_RIGHT = (255, 100, 0, 50)

    grad = Image.new("RGBA", (W, H), TOP_LEFT)
    gpix = grad.load()
    for y in range(H):
        for x in range(W):
            t = (x / W + y / H) / 2
            gpix[x, y] = (
                int(TOP_LEFT[0] + (BOTTOM_RIGHT[0] - TOP_LEFT[0]) * t),
                int(TOP_LEFT[1] + (BOTTOM_RIGHT[1] - TOP_LEFT[1]) * t),
                int(TOP_LEFT[2] + (BOTTOM_RIGHT[2] - TOP_LEFT[2]) * t),
                200,
            )

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIUS, fill=255)
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card.paste(grad, (0, 0), mask)

    draw = ImageDraw.Draw(card)

    avatar_size = 118
    avatar_x, avatar_y = 55, (H - avatar_size) // 2

    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((avatar_size, avatar_size))
    amask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(amask).ellipse([0, 0, avatar_size, avatar_size], fill=255)
    card.paste(avatar_img, (avatar_x, avatar_y), amask)
    draw = ImageDraw.Draw(card)

    text_x = avatar_x + avatar_size + 40
    max_text_width = W - text_x - 40

    title_text = f"Chào Mừng Đến Với {guild_name}! 😊"
    title_font = _font(FONT_BOLD, 32)
    draw.text((text_x, 55), title_text, font=title_font, fill=(255, 255, 255, 255))

    user_text = f"@{username}"
    user_font = _font(FONT_BOLD, 26)
    draw.text((text_x, 105), user_text, font=user_font, fill=(255, 215, 0, 255))

    draw.text((text_x, 150), "Đã Đặt Chân Đến Thế Giới Mèo! 🐾", 
               font=_font(FONT_REGULAR, 18), fill=(255, 255, 255, 220))
    draw.text((text_x, 180), "Hãy Cùng Nhau Vui Chơi Và Kết Bạn Nhé! 😁", 
               font=_font(FONT_REGULAR, 16), fill=(255, 255, 255, 180))

    badge_text = f"Thành Viên #{member_number}"
    badge_font = _font(FONT_BOLD, 18)
    btw = draw.textlength(badge_text, font=badge_font)
    pad_x = 22
    badge_w = btw + pad_x * 2
    badge_h = 42
    badge_x2 = W - 40
    badge_x1 = badge_x2 - badge_w
    badge_y1 = H - 62
    badge_y2 = badge_y1 + badge_h
    draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2],
                            radius=badge_h // 2, fill=(255, 165, 0, 255))
    tb = draw.textbbox((0, 0), badge_text, font=badge_font)
    th = tb[3] - tb[1]
    draw.text((badge_x1 + pad_x, badge_y1 + (badge_h - th) // 2 - tb[1]),
              badge_text, font=badge_font, fill=(255, 255, 255, 255))

    buffer = io.BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def build_welcome_card_file(member: discord.Member) -> discord.File:
    avatar_bytes = await member.display_avatar.replace(size=256, format="png").read()
    buffer = await bot.loop.run_in_executor(
        None,
        generate_welcome_card,
        avatar_bytes,
        str(member),
        member.guild.member_count,
        member.guild.name,
    )
    return discord.File(buffer, filename="welcome_card.png")

# ── Giao Diện Welcome ──────────────────────────────────────────────────────
class WelcomeView(discord.ui.LayoutView):
    def __init__(self, member: discord.Member, rules_channel_id: int | None,
                 ping_role_id: int | None, intro_channel_id: int | None):
        super().__init__()
        guild = member.guild

        ping_text = ""
        if ping_role_id:
            role = guild.get_role(ping_role_id)
            if role is not None:
                ping_text = f"{role.mention} "

        container = discord.ui.Container(accent_colour=ACCENT_COLOUR)

        container.add_item(discord.ui.TextDisplay(
            f"## 🐱 {ping_text}Chào Mừng {member.name} Đến Với {guild.name}!"
        ))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            f"{member.mention} Đã Chính Thức Gia Nhập Đại Gia Đình Những Chú Mèo Đáng Yêu! 🎉🎉\n"
            f"Chúc Bạn Có Thật Nhiều Trải Nghiệm Vui Vẻ Và Kết Bạn Thật Nhiều Nhé!"
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            f"**👤 Tên:** {member.name}"
        ))
        container.add_item(discord.ui.Separator())

        gallery = discord.ui.MediaGallery()
        gallery.add_item(media="attachment://welcome_card.png")
        container.add_item(gallery)
        container.add_item(discord.ui.Separator())

        rules_channel = None
        if rules_channel_id:
            rules_channel = guild.get_channel(rules_channel_id)
        if rules_channel is None:
            rules_channel = guild.rules_channel
        rules_text = rules_channel.mention if rules_channel else "📜 Kênh Nội Quy"

        intro_channel = None
        if intro_channel_id:
            intro_channel = guild.get_channel(intro_channel_id)
        intro_text = intro_channel.mention if intro_channel else "💬 #Giới-Thiệu"

        container.add_item(discord.ui.TextDisplay(
            "**🚀 Gợi Ý Dành Cho Bạn**\n\n"
            f"📌 Đọc {rules_text} Để Nắm Rõ Nội Quy Server\n"
            f"💬 Ghé {intro_text} Để Giới Thiệu Bản Thân Nhé\n"
            f"🎮 Kết Bạn Và Cùng Nhau Chiến Game Vui Vẻ\n"
            f"🐱 Đừng Ngần Ngại Đặt Câu Hỏi Nếu Cần Giúp Đỡ!"
        ))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(
            f"-# 💌 Cảm Ơn Bạn Đã Đồng Hành Cùng **{guild.name}** ❤️"
        ))

        self.add_item(container)

# ── Khối Chào Mừng Thứ 2 ──────────────────────────────────────────────────
def _format_embed2_text(template: str, member: discord.Member, ping_role_id: int | None) -> str:
    guild = member.guild

    ping_text = ""
    ping_message = ""
    if ping_role_id:
        role = guild.get_role(ping_role_id)
        if role is not None:
            ping_text = f"{role.mention} "
            ping_message = f"{role.mention} Hãy Cùng Nhau Chào Đón Thành Viên Mới Này Nhé! 😁😁😁"

    return template.format(
        member=member.mention,
        member_name=member.name,
        member_display=member.display_name,
        guild=guild.name,
        ping=ping_text,
        ping_message=ping_message,
    )

class WelcomeEmbed2View(discord.ui.LayoutView):
    def __init__(self, member: discord.Member, ping_role_id: int | None, cfg: dict):
        super().__init__()
        guild = member.guild

        title_tpl = cfg.get("embed2_title", DEFAULT_EMBED2_TITLE)
        desc_tpl = cfg.get("embed2_desc", DEFAULT_EMBED2_DESC)
        footer_tpl = cfg.get("embed2_footer", DEFAULT_EMBED2_FOOTER)

        title_text = _format_embed2_text(title_tpl, member, ping_role_id)
        desc_text = _format_embed2_text(desc_tpl, member, ping_role_id)
        footer_text = _format_embed2_text(footer_tpl, member, ping_role_id)

        container = discord.ui.Container(accent_colour=discord.Colour.gold())

        container.add_item(discord.ui.TextDisplay(f"## {title_text}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

        section = discord.ui.Section(
            discord.ui.TextDisplay(desc_text),
            accessory=discord.ui.Thumbnail(media=member.display_avatar.url),
        )
        container.add_item(section)
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"-# {footer_text}"))

        self.add_item(container)

# ── Sự Kiện ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Đã Đăng Nhập: {bot.user} (ID: {bot.user.id})")
    print(f"🐱 Meow Town Bot Đã Sẵn Sàng!")
    print(f"👑 Owner ID: {OWNER_ID}")
    
    # Kiểm tra font
    if os.path.exists(FONT_BOLD) and os.path.exists(FONT_REGULAR):
        print(f"✅ Đã tìm thấy font tại: {FONT_DIR}")
    else:
        print(f"⚠️ Không tìm thấy font tại {FONT_DIR}")
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã Đồng Bộ {len(synced)} Slash Commands!")
        for cmd in synced:
            print(f"  • /{cmd.name}")
    except Exception as e:
        print(f"❌ Lỗi Đồng Bộ Slash Commands: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    cfg = get_guild_config(member.guild.id)
    channel_id = cfg.get("welcome_channel")
    channel = member.guild.get_channel(channel_id) if channel_id else None

    if channel is None:
        channel = member.guild.system_channel

    if channel is not None:
        try:
            file = await build_welcome_card_file(member)
            view = WelcomeView(
                member, 
                cfg.get("rules_channel"), 
                cfg.get("ping_role"),
                cfg.get("intro_channel")
            )
            allowed = discord.AllowedMentions(users=True, roles=True, everyone=False)
            await channel.send(view=view, file=file, allowed_mentions=allowed)
        except Exception as e:
            print(f"❌ Lỗi tạo ảnh welcome: {e}")
            await channel.send(f"🎉 Chào mừng {member.mention} đến với server!")
        
        intro_channel_id = cfg.get("intro_channel")
        intro_channel = member.guild.get_channel(intro_channel_id) if intro_channel_id else None
        
        if intro_channel is not None and intro_channel != channel:
            view2 = WelcomeEmbed2View(member, cfg.get("ping_role"), cfg)
            await intro_channel.send(view=view2, allowed_mentions=allowed)
        else:
            view2 = WelcomeEmbed2View(member, cfg.get("ping_role"), cfg)
            await channel.send(view=view2, allowed_mentions=allowed)

# ── Slash Commands ──────────────────────────────────────────────────────────
@bot.tree.command(name="setwelcome", description="Cấu Hình Hệ Thống Chào Mừng")
@app_commands.describe(
    channel="Kênh Sẽ Nhận Tin Nhắn Chào Mừng",
    rules_channel="(Tuỳ Chọn) Kênh Nội Quy Server",
    intro_channel="(Tuỳ Chọn) Kênh Giới Thiệu Bản Thân",
    ping_role="(Tuỳ Chọn) Role Sẽ Được Tag Khi Có Thành Viên Mới",
)
async def setwelcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    rules_channel: discord.TextChannel | None = None,
    intro_channel: discord.TextChannel | None = None,
    ping_role: discord.Role | None = None,
):
    if not await owner_only(interaction):
        return
    
    update_guild_config(
        interaction.guild_id,
        welcome_channel=channel.id,
        rules_channel=rules_channel.id if rules_channel else None,
        intro_channel=intro_channel.id if intro_channel else None,
        ping_role=ping_role.id if ping_role else None,
    )

    fields = {
        "📌 Kênh Chào Mừng": channel.mention,
        "📋 Kênh Nội Quy": rules_channel.mention if rules_channel else "Không Có",
        "💬 Kênh Giới Thiệu": intro_channel.mention if intro_channel else "Không Có",
        "🔔 Role Ping": ping_role.mention if ping_role else "Không Có"
    }
    
    view = discord.ui.LayoutView()
    items = [
        discord.ui.TextDisplay("## ✅ Thiết Lập Thành Công!"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small)
    ]
    for key, value in fields.items():
        items.append(discord.ui.TextDisplay(f"**{key}**\n{value}"))
        items.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    container = discord.ui.Container(*items)
    view.add_item(container)
    
    await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="setwelcomeembed2", description="Tuỳ Chỉnh Nội Dung Khối Chào Mừng Thứ 2")
@app_commands.describe(
    title="Tiêu Đề. Placeholder: {member} {member_name} {member_display} {guild} {ping} {ping_message}",
    description="Nội Dung. Placeholder: {member} {member_name} {member_display} {guild} {ping} {ping_message}",
    footer="Dòng Chữ Nhỏ Ở Cuối. Cùng Placeholder Như Trên",
    reset="Đặt True Để Khôi Phục Về Mặc Định",
)
async def setwelcomeembed2(
    interaction: discord.Interaction,
    title: str | None = None,
    description: str | None = None,
    footer: str | None = None,
    reset: bool | None = None,
):
    if not await owner_only(interaction):
        return
    
    if reset:
        update_guild_config(
            interaction.guild_id,
            embed2_title=DEFAULT_EMBED2_TITLE,
            embed2_desc=DEFAULT_EMBED2_DESC,
            embed2_footer=DEFAULT_EMBED2_FOOTER,
        )
    else:
        update_guild_config(
            interaction.guild_id,
            embed2_title=title,
            embed2_desc=description,
            embed2_footer=footer,
        )

    cfg = get_guild_config(interaction.guild_id)

    try:
        preview = WelcomeEmbed2View(interaction.user, cfg.get("ping_role"), cfg)
        await interaction.response.send_message(
            content="✅ Đã Lưu Cấu Hình! Xem Trước Bên Dưới:",
            view=preview,
            ephemeral=True,
        )
    except (KeyError, IndexError) as e:
        await interaction.response.send_message(
            f"⚠️ Placeholder Không Hợp Lệ: `{e}`",
            ephemeral=True,
        )

@bot.tree.command(name="testwelcome", description="Xem Trước Tin Nhắn Chào Mừng")
async def testwelcome(interaction: discord.Interaction):
    if not await owner_only(interaction):
        return
    
    await interaction.response.defer(ephemeral=True)
    cfg = get_guild_config(interaction.guild_id)
    
    try:
        file = await build_welcome_card_file(interaction.user)
        view = WelcomeView(
            interaction.user, 
            cfg.get("rules_channel"), 
            cfg.get("ping_role"),
            cfg.get("intro_channel")
        )
        await interaction.followup.send(view=view, file=file, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi tạo ảnh: {e}", ephemeral=True)
    
    view2 = WelcomeEmbed2View(interaction.user, cfg.get("ping_role"), cfg)
    await interaction.followup.send(view=view2, ephemeral=True)

@bot.tree.command(name="ping", description="Kiểm Tra Độ Trễ Của Bot")
async def ping(interaction: discord.Interaction):
    if not await owner_only(interaction):
        return
    
    latency = round(bot.latency * 1000)
    status = "🟢 Online" if latency < 200 else "🟡 Chậm" if latency < 400 else "🔴 Rất Chậm"
    
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay("## 🏓 Pong!"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(f"**📡 Độ Trễ:** `{latency}ms`\n**🔄 Trạng Thái:** {status}")
    )
    view.add_item(container)
    await interaction.response.send_message(view=view, ephemeral=True)

# ── Lệnh Sync ──────────────────────────────────────────────────────────────
@bot.command(name="sync")
async def sync(ctx: commands.Context):
    if ctx.author.id != OWNER_ID:
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay("## ❌ Từ Chối Quyền"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay("⚠️ Chỉ **Chủ Bot** Mới Có Thể Dùng Lệnh Này!")
        )
        view.add_item(container)
        await ctx.send(view=view)
        return

    try:
        synced_global = await bot.tree.sync()
        msg = f"✅ Đã Đồng Bộ {len(synced_global)} Slash Command (Global)."

        if ctx.guild is not None:
            bot.tree.copy_global_to(guild=ctx.guild)
            synced_guild = await bot.tree.sync(guild=ctx.guild)
            msg += f"\n⚡ Đã Đồng Bộ Ngay {len(synced_guild)} Lệnh Cho Server Này."
        
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay("## ✅ Thành Công!"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(msg)
        )
        view.add_item(container)
        await ctx.send(view=view)
    except Exception as e:
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay("## ❌ Lỗi"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(str(e))
        )
        view.add_item(container)
        await ctx.send(view=view)

# ── Error Handlers ──────────────────────────────────────────────────────────
@bot.tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    error_msg = str(error)
    
    if isinstance(error, app_commands.MissingPermissions):
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay("## ❌ Không Có Quyền!"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay("Bạn Không Có Quyền Sử Dụng Lệnh Này")
        )
        view.add_item(container)
        try:
            await interaction.response.send_message(view=view, ephemeral=True)
        except:
            pass
    else:
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay("## ❌ Đã Xảy Ra Lỗi!"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(f"```{error_msg[:200]}```")
        )
        view.add_item(container)
        try:
            await interaction.response.send_message(view=view, ephemeral=True)
        except:
            pass

# ── Điểm Khởi Chạy ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit(
            "❌ Không Tìm Thấy DISCORD_TOKEN. Hãy Tạo File .Env Và Điền Token."
        )
    bot.run(TOKEN)
