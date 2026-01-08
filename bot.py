import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- ENV VARIABLES ----------
API_TOKEN = os.getenv("BOT_TOKEN")  # Render/Env Variables orqali oladi
SUPER_ADMIN = int(os.getenv("SUPER_ADMIN"))  # Render/Env Variables orqali oladi

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------- DATABASE ----------
db = sqlite3.connect("bot.db")
cursor = db.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    file_id TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS channels (
    username TEXT PRIMARY KEY
)""")

cursor.execute("INSERT OR IGNORE INTO admins VALUES (?)", (SUPER_ADMIN,))
db.commit()

# ---------- HELPERS ----------
async def is_admin(uid: int) -> bool:
    cursor.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,))
    return cursor.fetchone() is not None

async def check_sub(uid: int) -> bool:
    cursor.execute("SELECT username FROM channels")
    chans = cursor.fetchall()
    for (ch,) in chans:
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status == "left":
                return False
        except:
            return False
    return True

def sub_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    cursor.execute("SELECT username FROM channels")
    for (ch,) in cursor.fetchall():
        kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return kb

def admin_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie"),
        InlineKeyboardButton("📢 Kanal qo‘shish", callback_data="add_channel")
    )
    kb.add(
        InlineKeyboardButton("📋 Kanallar", callback_data="list_channel"),
        InlineKeyboardButton("📊 Statistika", callback_data="stats")
    )
    return kb

# ---------- FSM ----------
class AddMovie(StatesGroup):
    video = State()
    code = State()

class AddChannel(StatesGroup):
    username = State()

# ---------- START ----------
@dp.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    if await check_sub(msg.from_user.id):
        await msg.answer("🎬 Kino kodini yuboring")
    else:
        await msg.answer(
            "❗ *Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling va Tekshirish tugmasini bosing!*",
            reply_markup=sub_keyboard(),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_cb(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("✅ Obuna tasdiqlandi!\n\n🎬 Kino kodini yuboring")
    else:
        await call.answer("❌ Hali obuna bo‘lmagansiz", show_alert=True)

# ---------- ADMIN ----------
@dp.message(Command("admin"))
async def admin_panel(msg: types.Message):
    if await is_admin(msg.from_user.id):
        await msg.answer("👑 Admin panel", reply_markup=admin_keyboard())

@dp.callback_query(lambda c: c.data == "add_movie")
async def add_movie(call: types.CallbackQuery, state: FSMContext):
    if await is_admin(call.from_user.id):
        await call.message.answer("🎥 Kinoni yuboring")
        await state.set_state(AddMovie.video)

@dp.message(lambda m: m.video is not None, state=AddMovie.video)
async def movie_video(msg: types.Message, state: FSMContext):
    await state.update_data(file_id=msg.video.file_id)
    await msg.answer("🔢 Kino kodini kiriting")
    await state.set_state(AddMovie.code)

@dp.message(state=AddMovie.code)
async def movie_code(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        cursor.execute("INSERT INTO movies VALUES (?,?)", (msg.text, data["file_id"]))
        db.commit()
        await msg.answer("✅ Kino saqlandi")
    except:
        await msg.answer("❌ Bu kod band")
    await state.clear()

@dp.callback_query(lambda c: c.data == "add_channel")
async def add_channel(call: types.CallbackQuery, state: FSMContext):
    if await is_admin(call.from_user.id):
        await call.message.answer("📢 Kanal username kiriting\nMasalan: @kanalim")
        await state.set_state(AddChannel.username)

@dp.message(state=AddChannel.username)
async def save_channel(msg: types.Message, state: FSMContext):
    try:
        cursor.execute("INSERT INTO channels VALUES (?)", (msg.text,))
        db.commit()
        await msg.answer("✅ Kanal qo‘shildi")
    except:
        await msg.answer("❌ Bu kanal mavjud")
    await state.clear()

@dp.callback_query(lambda c: c.data == "list_channel")
async def list_channel(call: types.CallbackQuery):
    cursor.execute("SELECT username FROM channels")
    chans = cursor.fetchall()
    text = "📋 Majburiy kanallar:\n"
    for i, (c,) in enumerate(chans, 1):
        text += f"{i}. {c}\n"
    await call.message.answer(text)

@dp.callback_query(lambda c: c.data == "stats")
async def stats(call: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*) FROM movies")
    movies = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM channels")
    chans = cursor.fetchone()[0]
    await call.message.answer(f"📊 Statistika:\n🎬 Kinolar: {movies}\n📢 Kanallar: {chans}")

# ---------- USER ----------
@dp.message()
async def get_movie(msg: types.Message):
    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Avval obuna bo‘ling", reply_markup=sub_keyboard())
        return
    cursor.execute("SELECT file_id FROM movies WHERE code=?", (msg.text,))
    row = cursor.fetchone()
    if row:
        await bot.send_video(msg.chat.id, row[0])
    else:
        await msg.answer("❌ Kino topilmadi")

# ---------- RUN ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
