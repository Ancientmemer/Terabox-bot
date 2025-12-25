from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.enums import ChatAction
import sqlite3
import re
import threading
import time
import asyncio
import requests
from flask import Flask
from config import *

# ==============================
# 🌐 UPTIME ROBOT WEB SERVER
# ==============================
web = Flask(__name__)

@web.route("/")
def home():
    return "✅ Terabox Bot is Alive"

def run_web():
    web.run(host="0.0.0.0", port=8080)

# ==============================
# 📦 DATABASE
# ==============================
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

# ==============================
# 🧠 TEMP STORAGE
# ==============================
user_links = {}
cancel_requests = set()

# ==============================
# 🤖 BOT
# ==============================
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ==============================
# 🎛 KEYBOARDS
# ==============================
choice_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⬇️ Download Link", callback_data="dl_link"),
        InlineKeyboardButton("📁 Upload as File", callback_data="upload_file")
    ]
])

cancel_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_dl")]
])

# ==============================
# ⏳ ANIMATIONS
# ==============================
async def progress_animation(msg):
    steps = [
        ("⏳ Fetching Terabox data...", "⬜⬜⬜⬜⬜ 0%"),
        ("🔄 Generating download link...", "🟩🟩⬜⬜⬜ 40%"),
        ("📦 Preparing file...", "🟩🟩🟩🟩⬜ 80%"),
    ]
    for text, bar in steps:
        try:
            await msg.edit_text(f"{text}\n\n{bar}", reply_markup=cancel_keyboard)
            await asyncio.sleep(1.2)
        except:
            pass

async def send_typing(app, chat_id, seconds=3):
    for _ in range(seconds):
        try:
            await app.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(1)
        except:
            break

# ==============================
# 🔗 TERABOX EXTRACTOR
# ==============================
def extract_terabox(url):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.terabox.com/"
    }

    r = session.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        return None

    token = re.search(r'jsToken":"(.*?)"', r.text)
    if not token:
        return None
    js_token = token.group(1)

    surl = re.search(r'surl=([a-zA-Z0-9_-]+)', url)
    if not surl:
        return None
    surl = surl.group(1)

    api = (
        "https://www.terabox.com/share/list"
        f"?app_id=250528&shorturl={surl}&jsToken={js_token}&page=1&num=1"
    )

    data = session.get(api, headers=headers, timeout=15).json()
    if "list" not in data or not data["list"]:
        return None

    return data["list"][0].get("dlink")

# ==============================
# 🚀 COMMANDS
# ==============================
@app.on_message(filters.command("start"))
async def start(_, msg):
    add_user(msg.from_user.id)
    await msg.reply_text(
        "👋 **Welcome to Terabox Downloader Bot**\n\n"
        "📥 Send any Terabox link\n"
        "🎥 Choose download type\n\n"
        "Use /help for more info",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("JOIN OUR COMMUNITY", url="https://t.me/jb_links")]
        ])
    )

@app.on_message(filters.command("help"))
async def help_cmd(_, msg):
    await msg.reply_text(
        "📌 **How to use**\n\n"
        "1️⃣ Send Terabox link\n"
        "2️⃣ Choose option\n"
        "3️⃣ Get file / link\n"
    )

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(_, msg):
    await msg.reply_text(f"👥 Total Users: **{len(get_users())}**")

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID) & filters.reply)
async def broadcast(_, msg):
    sent = 0
    for user in get_users():
        try:
            await msg.reply_to_message.copy(user)
            sent += 1
        except:
            pass
    await msg.reply_text(f"✅ Broadcast sent to **{sent}** users")

# ==============================
# 🔗 LINK HANDLER
# ==============================
@app.on_message(filters.text & ~filters.regex("^/"))
async def link_handler(_, msg):
    if not re.search(r"(terabox|1024tera)", msg.text, re.I):
        return

    user_links[msg.from_user.id] = msg.text
    await msg.reply_text(
        "🔽 **Choose download method:**",
        reply_markup=choice_keyboard
    )

# ==============================
# ❌ CANCEL
# ==============================
@app.on_callback_query(filters.regex("cancel_dl"))
async def cancel_dl(_, q):
    cancel_requests.add(q.from_user.id)
    await q.message.edit_text("❌ Download cancelled.")

# ==============================
# ⬇️ MAIN CALLBACK
# ==============================
@app.on_callback_query(filters.regex("dl_link|upload_file"))
async def handle_download(app, q: CallbackQuery):
    uid = q.from_user.id
    if uid not in user_links:
        await q.answer("❌ Link expired", show_alert=True)
        return

    cancel_requests.discard(uid)
    link = user_links[uid]
    start_time = time.time()

    msg = q.message
    await msg.edit_text("⏳ Starting...", reply_markup=cancel_keyboard)
    await send_typing(app, msg.chat.id)
    await progress_animation(msg)

    if uid in cancel_requests:
        cancel_requests.discard(uid)
        return

    file_url = extract_terabox(link)
    if not file_url:
        await msg.edit_text("❌ Failed to extract link.")
        return

    t = round(time.time() - start_time, 2)

    if q.data == "dl_link":
        await msg.edit_text(
            f"⬇️ **Download Link Ready**\n\n{file_url}\n\n"
            f"⏱️ Time taken: `{t}s`"
        )
    else:
        try:
            await msg.delete()
            await q.message.reply_document(
                file_url,
                caption=f"📁 Uploaded\n⏱️ Time taken: `{t}s`"
            )
        except:
            await q.message.reply_text(
                f"⚠️ File too large\n\n⬇️ {file_url}"
            )

    user_links.pop(uid, None)
    cancel_requests.discard(uid)

# ==============================
# ▶️ RUN
# ==============================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    app.run()
