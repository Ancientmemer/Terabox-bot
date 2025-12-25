from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatAction
import sqlite3, re, threading, time, asyncio, requests, urllib.parse
from flask import Flask
from config import *

# ==============================
# 🌐 UPTIME SERVER
# ==============================
web = Flask(__name__)

@web.route("/")
def home():
    return "✅ Terabox Bot Alive"

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
        InlineKeyboardButton("⬇️ Download Link", callback_data="dl"),
        InlineKeyboardButton("📁 Upload as File", callback_data="up")
    ]
])

cancel_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
])

# ==============================
# ⏳ UI EFFECTS
# ==============================
async def typing(app, chat):
    for _ in range(3):
        await app.send_chat_action(chat, ChatAction.TYPING)
        await asyncio.sleep(1)

async def progress(msg):
    stages = [
        "⏳ Fetching data...",
        "🔄 Processing link...",
        "📦 Preparing result..."
    ]
    for s in stages:
        await msg.edit_text(s, reply_markup=cancel_keyboard)
        await asyncio.sleep(1.2)

# ==============================
# 🔗 GITHUB EXTRACTOR (TRY 1)
# ==============================
def github_extract(url):
    try:
        s = requests.Session()
        h = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.terabox.com/"
        }

        r = s.get(url, headers=h, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            return None

        m = re.search(r"/s/([A-Za-z0-9_-]+)", r.url)
        if not m:
            return None
        surl = m.group(1)

        api = "https://www.terabox.com/share/listshare"
        p = {
            "app_id": "250528",
            "shorturl": surl,
            "root": "1",
            "page": "1",
            "num": "1"
        }

        j = s.get(api, headers=h, params=p, timeout=15).json()
        fs_id = j["list"][0]["fs_id"]

        d = s.get(
            "https://www.terabox.com/share/download",
            headers=h,
            params={"app_id": "250528", "fs_id": fs_id},
            timeout=15
        ).json()

        return d.get("dlink")
    except:
        return None

# ==============================
# 🌐 FREE API FALLBACK (TRY 2)
# ==============================
def api_extract(url):
    try:
        api = f"https://terabox-dl.vercel.app/api?url={url}"
        r = requests.get(api, timeout=20).json()
        return r.get("download_url")
    except:
        return None

# ==============================
# 🚀 COMMANDS
# ==============================
@app.on_message(filters.command("start"))
async def start(_, m):
    add_user(m.from_user.id)
    await m.reply_text(
        "👋 **Terabox Downloader Bot**\n\n"
        "📥 Send any Terabox share link\n"
        "⚡ Works with most public links",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("JOIN OUR COMMUNITY", url="https://t.me/jb_links")]
        ])
    )

@app.on_message(filters.command("help"))
async def help_cmd(_, m):
    await m.reply_text(
        "📌 **Usage**\n\n"
        "1️⃣ Send Terabox link\n"
        "2️⃣ Choose download method\n"
        "3️⃣ Enjoy 😄"
    )

# ==============================
# 🔗 LINK HANDLER
# ==============================
@app.on_message(filters.text & ~filters.regex("^/"))
async def link_handler(_, m):
    text = m.text.strip()
    if not re.search(r"https?://.+/s/[A-Za-z0-9_-]+", text):
        return

    user_links[m.from_user.id] = text
    await m.reply_text("🔽 Choose download method:", reply_markup=choice_keyboard)

# ==============================
# ❌ CANCEL
# ==============================
@app.on_callback_query(filters.regex("cancel"))
async def cancel(_, q):
    cancel_requests.add(q.from_user.id)
    await q.message.edit_text("❌ Cancelled")

# ==============================
# ⬇️ MAIN FLOW
# ==============================
@app.on_callback_query(filters.regex("dl|up"))
async def main(app, q: CallbackQuery):
    uid = q.from_user.id
    if uid not in user_links:
        await q.answer("Link expired", show_alert=True)
        return

    cancel_requests.discard(uid)
    link = user_links[uid]
    start = time.time()

    msg = q.message
    await typing(app, msg.chat.id)
    await progress(msg)

    if uid in cancel_requests:
        return

    # TRY 1
    file_url = github_extract(link)

    # TRY 2
    if not file_url:
        file_url = api_extract(link)

    if not file_url:
        await msg.edit_text("❌ Unable to fetch link. Try another.")
        return

    t = round(time.time() - start, 2)

    if q.data == "dl":
        await msg.edit_text(
            f"⬇️ **Download Link Ready**\n\n{file_url}\n\n⏱ `{t}s`"
        )
    else:
        try:
            await msg.delete()
            await q.message.reply_document(
                file_url,
                caption=f"📁 Uploaded\n⏱ `{t}s`"
            )
        except:
            await q.message.reply_text(f"⬇️ {file_url}")

    user_links.pop(uid, None)
    cancel_requests.discard(uid)

# ==============================
# ▶️ RUN
# ==============================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    app.run()
