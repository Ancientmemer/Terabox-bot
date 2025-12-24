from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import re
from config import *

# ---------- Database ----------
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
db.commit()

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    db.commit()

def get_users():
    cursor.execute("SELECT id FROM users")
    return [x[0] for x in cursor.fetchall()]

# ---------- Bot ----------
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ---------- START ----------
@app.on_message(filters.command("start"))
async def start(_, msg):
    add_user(msg.from_user.id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("JOIN OUR COMMUNITY", url="https://t.me/jb_links")]
    ])

    await msg.reply_text(
        "👋 **Welcome to Terabox Downloader Bot**\n\n"
        "📥 Send any Terabox link\n"
        "🎥 I will give you the video/file\n\n"
        "Use /help for more info",
        reply_markup=keyboard
    )

# ---------- HELP ----------
@app.on_message(filters.command("help"))
async def help_cmd(_, msg):
    await msg.reply_text(
        "📌 **How to use this bot**\n\n"
        "1️⃣ Copy Terabox video/file link\n"
        "2️⃣ Paste it here\n"
        "3️⃣ Wait for processing\n\n"
        "That's it 😄"
    )

# ---------- STATS ----------
@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(_, msg):
    users = get_users()
    await msg.reply_text(f"👥 Total Users: **{len(users)}**")

# ---------- BROADCAST ----------
@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID) & filters.reply)
async def broadcast(_, msg):
    users = get_users()
    sent = 0

    for user in users:
        try:
            await msg.reply_to_message.copy(user)
            sent += 1
        except:
            pass

    await msg.reply_text(f"✅ Broadcast sent to **{sent}** users")

# ---------- LINK HANDLER ----------
# Slash (/) commands ellam ignore cheyyum
@app.on_message(filters.text & ~filters.regex("^/"))
async def link_handler(_, msg):
    add_user(msg.from_user.id)

    text = msg.text
    if not re.search(r"(terabox|1024tera)", text, re.IGNORECASE):
        return

    await msg.reply_text("⏳ Processing your Terabox link...")

    # -----------------------------
    # TODO: Terabox extractor logic
    # -----------------------------
    # video_url = extract_terabox(text)
    # await msg.reply_video(video_url)

    await msg.reply_text(
        "⚠️ Terabox extractor not added yet.\n"
        "Plug extractor logic here."
    )

# ---------- RUN ----------
app.run()
