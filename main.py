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

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Tìm và load font từ hệ thống"""
    cache_key = (size, bold)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    # Danh sách font trên hệ thống Linux
    if bold:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        ]

    # Thử từng đường dẫn
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, size)
            _FONT_CACHE[cache_key] = font
            return font
        except:
            continue

    # Fallback: font mặc định
    try:
        font = ImageFont.load_default()
        _FONT_CACHE[cache_key] = font
        return font
    except:
        raise RuntimeError("❌ Không tìm thấy font nào!")

def generate_welcome_card(avatar_bytes: bytes, username: str, member_number: int,
                           guild_name: str) -> io.BytesIO:
    W, H = 800, 350  # Tăng chiều cao lên 350
    RADIUS = 30
    
    # Gradient nền đẹp hơn
    grad = Image.new("RGBA", (W, H))
    for y in range(H):
        for x in range(W):
            # Tạo gradient từ cam sang hồng
            t = y / H
            r = int(255 - 50 * t)
            g = int(165 - 80 * t)
            b = int(0 + 100 * t)
            grad.putpixel((x, y), (r, g, b, 200))
    
    # Bo góc
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIUS, fill=255)
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card.paste(grad, (0, 0), mask)
    
    draw = ImageDraw.Draw(card)
    
    # Avatar tròn
    avatar_size = 120
    avatar_x, avatar_y = 50, (H - avatar_size) // 2
    
    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((avatar_size, avatar_size))
    amask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(amask).ellipse([0, 0, avatar_size, avatar_size], fill=255)
    card.paste(avatar_img, (avatar_x, avatar_y), amask)
    
    # Vẽ viền cho avatar
    draw.ellipse([avatar_x - 3, avatar_y - 3, avatar_x + avatar_size + 3, avatar_y + avatar_size + 3],
                 outline=(255, 215, 0, 255), width=4)
    
    # Text bắt đầu từ đây
    text_x = avatar_x + avatar_size + 35
    text_y = 50
    
    # Dòng 1: Chào mừng
    try:
        font_title = _font(28, bold=True)
        title = f"Chào Mừng Đến Với {guild_name}! 😊"
        draw.text((text_x, text_y), title, font=font_title, fill=(255, 255, 255, 255))
    except:
        draw.text((text_x, text_y), f"Chào Mừng Đến Với {guild_name}!", fill=(255, 255, 255))
    
    # Dòng 2: Tên user
    try:
        font_name = _font(24, bold=True)
        draw.text((text_x, text_y + 45), f"@{username}", font=font_name, fill=(255, 215, 0, 255))
    except:
        draw.text((text_x, text_y + 45), f"@{username}", fill=(255, 215, 0))
    
    # Dòng 3: Slogan
    try:
        font_slogan = _font(16, bold=False)
        draw.text((text_x, text_y + 85), "🐾 Đã Đặt Chân Đến Thế Giới Mèo!", 
                  font=font_slogan, fill=(255, 255, 255, 220))
    except:
        draw.text((text_x, text_y + 85), "Đã Đặt Chân Đến Thế Giới Mèo!", fill=(255, 255, 255))
    
    # Dòng 4: Lời chúc
    try:
        font_greeting = _font(14, bold=False)
        draw.text((text_x, text_y + 115), "Hãy Cùng Nhau Vui Chơi Và Kết Bạn Nhé! 😁",
                  font=font_greeting, fill=(255, 255, 255, 180))
    except:
        draw.text((text_x, text_y + 115), "Hãy Cùng Nhau Vui Chơi Và Kết Bạn Nhé!", fill=(255, 255, 255))
    
    # Badge thành viên
    badge_text = f"# {member_number}"
    try:
        badge_font = _font(22, bold=True)
        # Đo chiều dài text
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        btw = bbox[2] - bbox[0]
        pad_x = 25
        badge_w = btw + pad_x * 2
        badge_h = 50
        badge_x2 = W - 30
        badge_x1 = badge_x2 - badge_w
        badge_y2 = H - 25
        badge_y1 = badge_y2 - badge_h
        
        # Vẽ badge
        draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2],
                               radius=badge_h // 2, fill=(255, 165, 0, 220))
        draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2],
                               radius=badge_h // 2, outline=(255, 215, 0, 255), width=2)
        
        # Text trong badge
        text_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        text_x_pos = badge_x1 + (badge_w - text_w) // 2
        text_y_pos = badge_y1 + (badge_h - text_h) // 2 - text_bbox[1]
        draw.text((text_x_pos, text_y_pos), badge_text, font=badge_font, fill=(255, 255, 255))
        
        # Thêm chữ "Thành Viên" phía trên badge
        member_label_font = _font(12, bold=False)
        label_text = "THÀNH VIÊN"
        label_bbox = draw.textbbox((0, 0), label_text, font=member_label_font)
        label_w = label_bbox[2] - label_bbox[0]
        label_x = badge_x1 + (badge_w - label_w) // 2
        draw.text((label_x, badge_y1 - 20), label_text, font=member_label_font, fill=(255, 215, 0, 200))
    except:
        # Fallback nếu lỗi font
        draw.text((W - 150, H - 40), f"#{member_number}", fill=(255, 255, 255))
    
    # Lưu ảnh
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

# ── Giao Diện Welcome (Components V2) ──────────────────────────────────────
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
