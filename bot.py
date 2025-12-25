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
import urllib.parse
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

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatAction
import sqlite3
import re
import threading
import time
import asyncio
import requests
import urllib.parse
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

def add_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
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
        ("📦 Preparing file...", "🟩🟩🟩🟩⬜ 80%")
    ]
    for t, bar in steps:
        try:
            await msg.edit_text(f"{t}\n\n{bar}", reply_markup=cancel_keyboard)
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
# 🔗 UPDATED TERABOX EXTRACTOR (GitHub-only)
# ==============================
def extract_terabox(url: str):
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.terabox.com/"
    }

    # 1️⃣ Open share page (cookies needed)
    r = session.get(url, headers=headers, allow_redirects=True, timeout=15)
    if r.status_code != 200:
        return None

    # 2️⃣ Extract shorturl (surl)
    parsed = urllib.parse.urlparse(r.url)
    qs = urllib.parse.parse_qs(parsed.query)

    if "surl" in qs:
        surl = qs["surl"][0]
    else:
        m = re.search(r"/s/([A-Za-z0-9_-]+)", r.url)
        if not m:
            return None
        surl = m.group(1)

    # 3️⃣ listshare API
    list_api = "https://www.terabox.com/share/listshare"
    params = {
        "app_id": "250528",
        "shorturl": surl,
        "root": "1",
        "page": "1",
        "num": "1"
    }

    res = session.get(list_api, headers=headers, params=params, timeout=15)
    try:
        data = res.json()
    except:
        return None

    if "list" not in data or not data["list"]:
        return None

    fs_id = data["list"][0].get("fs_id")
    if not fs_id:
        return None

    # 4️⃣ download API
    dl_api = "https://www.terabox.com/share/download"
    dparams = {
        "app_id": "250528",
        "fs_id": fs_id
    }

    dres = session.get(dl_api, headers=headers, params=dparams, timeout=15)
    try:
        djson = dres.json()
    except:
        return None

    return djson.get("dlink")

# ==============================
# 🚀 COMMANDS
# ==============================
@app.on_message(filters.command("start"))
async def start(_, msg):
    add_user(msg.from_user.id)
    await msg.reply_text(
        "👋 **Welcome to Terabox Downloader Bot**\n\n"
        "📥 Send any Terabox share link\n"
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
        "1️⃣ Send a Terabox share link\n"
        "2️⃣ Choose download option\n"
        "3️⃣ Get file or direct link"
    )

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(_, msg):
    await msg.reply_text(f"👥 Total Users: **{len(get_users())}**")

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID) & filters.reply)
async def broadcast(_, msg):
    sent = 0
    for u in get_users():
        try:
            await msg.reply_to_message.copy(u)
            sent += 1
        except:
            pass
    await msg.reply_text(f"✅ Broadcast sent to **{sent}** users")

# ==============================
# 🔗 LINK HANDLER (ALL TERABOX DOMAINS)
# ==============================
@app.on_message(filters.text & ~filters.regex("^/"))
async def link_handler(_, msg):
    text = msg.text.strip()

    # Accept ALL Terabox mirror domains ONLY with /s/
    pattern = r"https?://([a-z0-9\-]+\.)?(terabox|tera)[a-z0-9\-\.]*/s/[A-Za-z0-9_-]+"

    if not re.search(pattern, text, re.I):
        return

    user_links[msg.from_user.id] = text

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
        await msg.edit_text("❌ Failed to extract link.\n\n⚠️ This link may be private, expired, or blocked by Terabox.")
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
                f"⚠️ File too large for Telegram upload.\n\n⬇️ {file_url}"
            )

    user_links.pop(uid, None)
    cancel_requests.discard(uid)

# ==============================
# ▶️ RUN
# ==============================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    app.run()
