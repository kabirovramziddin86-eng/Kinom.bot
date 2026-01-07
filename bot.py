import telebot
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

# ========================
# CONFIG
# ========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPERADMIN_ID = 1230506568  # Sizning Telegram ID
PORT = int(os.environ.get("PORT", 4000))

if not BOT_TOKEN:
    print("BOT_TOKEN topilmadi!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# ========================
# JSON FILES
# ========================
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
kino = load_json(KINO_FILE)
users = load_json(USERS_FILE)

# ========================
# HELPERS
# ========================
def is_subscribed(user_id):
    # Kanalga obuna tekshirish (demo, doim True)
    return True

def add_user(user_id):
    if str(user_id) not in users:
        users[str(user_id)] = {"id": user_id}
        save_json(USERS_FILE, users)

# ========================
# FAKE WEB SERVER (RENDER FREE PLAN)
# ========================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    server = HTTPServer(("", PORT), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server).start()

# ========================
# USER HANDLERS
# ========================
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Tekshirish♻️", callback_data="check_channels"))
    bot.reply_to(
        message,
        "Salom 👋, botdan to‘liq foydalanish uchun quyidagi kanallarga obuna bo‘ling va Tekshirish♻️ tugmasini bosing!",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data == "check_channels")
def check_channels(call):
    user_id = call.from_user.id
    if is_subscribed(user_id):
        bot.send_message(user_id, "Salom, kerakli kino kodini yuboring")
    else:
        bot.send_message(user_id, "Siz kanallarga obuna bo‘lmadingiz!")

@bot.message_handler(func=lambda m: True)
def handle_kino_code(message):
    user_id = message.from_user.id
    code = message.text.strip()
    if code in kino:
        bot.reply_to(message, f"Kino linki: {kino[code]}")
    else:
        bot.reply_to(message, "Bunday kodli kino mavjud emas!")

# ========================
# ADMIN PANEL
# ========================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != SUPERADMIN_ID:
        bot.reply_to(message, "Siz admin emassiz ❌")
        return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Botdagi foydalanuvchilar", callback_data="admin_users"))
    markup.add(InlineKeyboardButton("Kino qo'shish", callback_data="admin_add_kino"))
    markup.add(InlineKeyboardButton("Kanal qo'shish", callback_data="admin_add_channel"))
    markup.add(InlineKeyboardButton("Kanallar ro'yxati", callback_data="admin_channels_list"))
    bot.reply_to(message, "Admin panel:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_"))
def admin_actions(call):
    user_id = call.from_user.id
    if user_id != SUPERADMIN_ID:
        bot.answer_callback_query(call.id, "Siz admin emassiz ❌")
        return

    data = call.data

    if data == "admin_users":
        msg = "Foydalanuvchilar:\n" + "\n".join([str(uid) for uid in users])
        bot.send_message(user_id, msg)

    elif data == "admin_add_kino":
        bot.send_message(user_id, "Kino qo'shish uchun kod va linkni quyidagi formatda yuboring:\nkod|link")
        bot.register_next_step_handler_by_chat_id(user_id, add_kino_step)

    elif data == "admin_add_channel":
        bot.send_message(user_id, "Kanal username ni yozing (@username)")
        bot.register_next_step_handler_by_chat_id(user_id, add_channel_step)

    elif data == "admin_channels_list":
        if not channels:
            bot.send_message(user_id, "Hozircha kanal mavjud emas")
            return
        for ch in channels:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("O'chirish", callback_data=f"remove_channel|{ch}"))
            bot.send_message(user_id, f"{ch}", reply_markup=markup)

    elif data.startswith("remove_channel|"):
        ch = data.split("|")[1]
        if ch in channels:
            channels.remove(ch)
            save_json(CHANNELS_FILE, channels)
            bot.answer_callback_query(call.id, f"{ch} o'chirildi ✅")
        else:
            bot.answer_callback_query(call.id, "Kanal topilmadi ❌")

# ========================
# ADMIN STEP HANDLERS
# ========================
def add_kino_step(message):
    try:
        code, link = message.text.strip().split("|")
        kino[code] = link
        save_json(KINO_FILE, kino)
        bot.send_message(message.from_user.id, f"Kino qo'shildi ✅\nKod: {code}")
    except:
        bot.send_message(message.from_user.id, "Format xato! Kod|link tarzida yuboring.")

def add_channel_step(message):
    ch = message.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch
    if ch not in channels:
        channels.append(ch)
        save_json(CHANNELS_FILE, channels)
        bot.send_message(message.from_user.id, f"Kanal qo'shildi ✅ {ch}")
    else:
        bot.send_message(message.from_user.id, "Kanal oldin qo'shilgan")

# ========================
# START BOT
# ========================
print("Bot ishga tushdi...")
bot.infinity_polling()
