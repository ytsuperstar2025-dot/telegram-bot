import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode
from io import BytesIO

from config import TOKEN, ADMIN_ID
from db import add_user, set_setting, get_setting, get_all_users

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

admin_wait = {}
offer_price = {}


# =========================
# STORE (ONLY PHOTO FIX HERE)
# =========================
def get_store():
    return {
        "upi": get_setting("upi", ""),
        "demo": get_setting("demo", ""),
        "price": get_setting("price", ""),
        "name": get_setting("name", ""),
        "premium_link": get_setting("premium_link", ""),
        "start_text": get_setting("start_text", ""),
        "photo": get_setting("photo", None),   # ✅ FIXED (NO str conversion)
        "sales": int(get_setting("sales", "0")),
        "revenue": int(get_setting("revenue", "0")),
    }


# =========================
# START (PHOTO FIX ONLY)
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    store = get_store()
    add_user(message.chat.id)

    text = store["start_text"] if store["start_text"] else "⚡ PAYMENT GATEWAY"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 BUY PREMIUM", callback_data="buy"))
    kb.add(InlineKeyboardButton("🎬 DEMO", url=store["demo"]))

    photo = store.get("photo")

    # ✅ FIXED SAFE PHOTO HANDLING
    if photo:
        try:
            bot.send_photo(message.chat.id, photo, caption=text, reply_markup=kb)
        except:
            bot.send_message(message.chat.id, text, reply_markup=kb)
    else:
        bot.send_message(message.chat.id, text, reply_markup=kb)


# =========================
# ADMIN PANEL (UNCHANGED)
# =========================
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        return

    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(InlineKeyboardButton("✏ SET NAME", callback_data="set_name"))
    kb.add(InlineKeyboardButton("💰 SET PRICE", callback_data="set_price"))
    kb.add(InlineKeyboardButton("🏦 SET UPI", callback_data="set_upi"))
    kb.add(InlineKeyboardButton("🎬 SET DEMO", callback_data="set_demo"))
    kb.add(InlineKeyboardButton("🔗 SET PREMIUM LINK", callback_data="set_premium"))
    kb.add(InlineKeyboardButton("🖼 SET PHOTO", callback_data="set_photo"))
    kb.add(InlineKeyboardButton("✏ SET START TEXT", callback_data="set_start_text"))

    kb.add(InlineKeyboardButton("👥 USERS", callback_data="users"))
    kb.add(InlineKeyboardButton("📊 STATS", callback_data="stats"))

    bot.send_message(message.chat.id, "👑 *ADMIN PANEL*", reply_markup=kb)


# =========================
# ADMIN INPUT (PHOTO FIX ONLY)
# =========================
@bot.message_handler(func=lambda m: m.from_user.id in admin_wait)
def save_admin(m):
    action = admin_wait[m.from_user.id]

    if action == "photo":
        if m.photo:
            file_id = m.photo[-1].file_id
            set_setting("photo", file_id)   # ✅ clean overwrite
            bot.send_message(m.chat.id, "🖼 PHOTO UPDATED SUCCESSFULLY")
        else:
            bot.send_message(m.chat.id, "❌ Send only photo")

        del admin_wait[m.from_user.id]
        return

    if action == "price":
        set_setting("price", m.text)

    elif action == "upi":
        set_setting("upi", m.text)

    elif action == "demo":
        set_setting("demo", m.text)

    elif action == "premium":
        set_setting("premium_link", m.text)

    elif action == "name":
        set_setting("name", m.text)

    elif action == "start_text":
        set_setting("start_text", m.text)

    del admin_wait[m.from_user.id]
    bot.send_message(m.chat.id, "✅ UPDATED SUCCESSFULLY!")


print("Bot Running...")
bot.infinity_polling(skip_pending=True)
