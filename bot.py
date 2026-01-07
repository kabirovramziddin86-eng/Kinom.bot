import telebot
import threading
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputMediaVideo, InputMediaDocument
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# CONFIG
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPERADMIN_ID = 1230506568  # Sizning Telegram ID
PORT = int(os.environ.get("PORT", 4000))

if not BOT_TOKEN:
    print("BOT_TOKEN topilmadi!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# JSON files
CHANNELS_FILE = "channels.json"
KINO_FILE = "kino.json"
USERS_FILE = "users.json"

def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return {} if filename != CHANNELS_FILE else []

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

channels = load_json(CHANNELS_FILE)
kino = load_json(KINO_FILE)  # { "kod": "file_id" }
users = load_json(USERS_FILE)  # { user_id: {"id": user_id} }

def add_user(user_id):
    if str(user_id) not in users:
        users[str(user_id)] = {"id": user_id}
        save_json(USERS_FILE, users)

# Fake web server (Render free plan)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

threading.Thread(target=lambda: HTTPServer(("", PORT), SimpleHandler).serve_forever()).start()

# Helper to check subscription
def is_subscribed(user_id, channel):
    try:
        member = bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ========================
# /start handler
# ========================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    add_user(user_id)

    if user_id == SUPERADMIN_ID:
        # Admin panel RKM
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("rkm: foydalanuvchilar"))
        markup.add(KeyboardButton("rkm: kino qo'shish"))
        markup.add(KeyboardButton("rkm: kanal qo'shish"))
        markup.add(KeyboardButton("rkm: kanallar ro'yxati"))
        bot.send_message(user_id, "Salom Admin 👑\nAdmin panel:", reply_markup=markup)
        return

    # Foydalanuvchi panel
    markup = InlineKeyboardMarkup()
    for ch in channels:
        markup.add(InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}"))
    markup.add(InlineKeyboardButton("Tekshirish♻️", callback_data="check_channels"))
    bot.send_message(user_id,
        "Salom 👋\nBotdan to‘liq foydalanish uchun quyidagi kanallarga obuna bo‘ling va Tekshirish♻️ tugmasini bosing!",
        reply_markup=markup
    )

# ========================
# Tekshirish tugmasi
# ========================
@bot.callback_query_handler(func=lambda c: c.data == "check_channels")
def check_channels(call):
    user_id = call.from_user.id
    all_ok = True
    for ch in channels:
        if not is_subscribed(user_id, ch):
            all_ok = False
            break
    if all_ok:
        msg = bot.send_message(user_id, "Siz barcha kanallarga obuna bo‘lgansiz ✅\nKerakli kino kodini yuboring:")
        bot.register_next_step_handler(msg, ask_kino_code)
    else:
        bot.send_message(user_id, "Barcha kanallarga obuna bo‘lmadingiz ❌")

# ========================
# Kino kodi so‘rash
# ========================
def ask_kino_code(message):
    user_id = message.from_user.id
    code = message.text.strip()
    if code in kino:
        bot.send_message(user_id, "Bunday kod allaqachon mavjud!")
        return
    # Endi media yuborishni so‘raysiz
    msg = bot.send_message(user_id, f"Kino faylini yuboring, bu kodga biriktiramiz: {code}")
    bot.register_next_step_handler(msg, receive_media, code)

def receive_media(message, code):
    user_id = message.from_user.id
    file_id = None

    # Video yoki document qabul qilish
    if message.content_type == 'video':
        file_id = message.video.file_id
    elif message.content_type == 'document':
        file_id = message.document.file_id
    else:
        msg = bot.send_message(user_id, "Faqat video yoki document yuboring!")
        bot.register_next_step_handler(msg, receive_media, code)
        return

    kino[code] = file_id
    save_json(KINO_FILE, kino)
    bot.send_message(user_id, f"Kino muvaffaqiyatli qo‘shildi ✅\nKod: {code}")

# ========================
# Admin RKM handler
# ========================
@bot.message_handler(func=lambda m: m.from_user.id == SUPERADMIN_ID)
def admin_rkm_handler(message):
    text = message.text
    user_id = message.from_user.id

    if text == "rkm: foydalanuvchilar":
        bot.send_message(user_id, f"Botdagi obunachilar soni: {len(users)}")

    elif text == "rkm: kino qo'shish":
        msg = bot.send_message(user_id, "Kino kodi bilan media fayl qo‘shish uchun kodi kiriting:")
        bot.register_next_step_handler(msg, ask_kino_code)

    elif text == "rkm: kanal qo'shish":
        msg = bot.send_message(user_id, "Kanal username ni kiriting (@username):")
        bot.register_next_step_handler(msg, add_channel_step)

    elif text == "rkm: kanallar ro'yxati":
        if not channels:
            bot.send_message(user_id, "Hozircha kanal mavjud emas")
        else:
            bot.send_message(user_id, "Kanallar: " + "\n".join(channels))

# ========================
# Admin step handler: add channel
# ========================
def add_channel_step(message):
    ch = message.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch
    if ch not in channels:
        channels.append(ch)
        save_json(CHANNELS_FILE, channels)
        bot.send_message(message.from_user.id, f"Kanal qo‘shildi ✅ {ch}")
    else:
        bot.send_message(message.from_user.id, "Kanal oldin qo‘shilgan")

# ========================
# Kino kodi orqali foydalanuvchi so‘rashi
# ========================
@bot.message_handler(func=lambda m: m.text in kino)
def send_kino_by_code(message):
    code = message.text.strip()
    file_id = kino.get(code)
    if not file_id:
        bot.send_message(message.from_user.id, "Bunday kodli kino mavjud emas!")
        return
    bot.send_message(message.from_user.id, "Kino tayyor! 🎬")
    bot.send_video(message.from_user.id, file_id)

# ========================
# START BOT
# ========================
print("Bot ishga tushdi...")
bot.infinity_polling()
