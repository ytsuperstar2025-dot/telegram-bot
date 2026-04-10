import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode
from io import BytesIO

from config import TOKEN, ADMIN_ID
from db import add_user, set_setting, get_setting

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")


# =========================
# STORE
# =========================
def get_store():
    return {
        "upi": get_setting("upi", "yourupi@bank"),
        "demo": get_setting("demo", ""),
        "price": get_setting("price", "29"),
        "name": get_setting("name", "Premium Access"),
        "premium_link": get_setting("premium_link", ""),
        "start_text": get_setting("start_text", ""),
        "sales": int(get_setting("sales", "0")),
        "revenue": int(get_setting("revenue", "0")),
        "photo": get_setting("photo", None)
    }


# =========================
# START (OLD STYLE RESTORED)
# =========================
def home_text(store):
    return f"*{store['name']}*\n\n{store['start_text']}\n\nPrice: Rs {store['price']}"


def home_markup(store):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Buy Premium", callback_data="buy"))
    kb.add(InlineKeyboardButton("🎬 Watch Demo", url=store["demo"]))
    return kb


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    store = get_store()
    add_user(message.chat.id)

    if store["photo"]:
        bot.send_photo(message.chat.id, store["photo"], caption=home_text(store), reply_markup=home_markup(store))
    else:
        bot.send_message(message.chat.id, home_text(store), reply_markup=home_markup(store))


# =========================
# BACK
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(c):
    store = get_store()
    bot.answer_callback_query(c.id)

    if store["photo"]:
        bot.send_photo(c.message.chat.id, store["photo"], caption=home_text(store), reply_markup=home_markup(store))
    else:
        bot.send_message(c.message.chat.id, home_text(store), reply_markup=home_markup(store))


# =========================
# BUY (QR)
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(c):
    store = get_store()
    bot.answer_callback_query(c.id)

    upi = store["upi"].strip()
    upi_link = f"upi://pay?pa={upi}&am={store['price']}&cu=INR"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    bio = BytesIO()
    bio.name = "qr.png"
    img.save(bio, "PNG")
    bio.seek(0)

    # ✅ FIXED VERTICAL BUTTON LAYOUT
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 I HAVE PAID", callback_data="paid"))
    kb.add(InlineKeyboardButton("❌ CANCEL ORDER", callback_data="cancel"))
    kb.add(InlineKeyboardButton("⬅ BACK", callback_data="back"))

    bot.send_photo(
        c.message.chat.id,
        bio,
        caption=home_text(store),
        reply_markup=kb
    )


# =========================
# CANCEL (₹2 OFFER)
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel_order(c):
    store = get_store()
    bot.answer_callback_query(c.id)

    new_price = int(store["price"]) - 2
    if new_price < 1:
        new_price = 1

    upi = store["upi"].strip()
    upi_link = f"upi://pay?pa={upi}&am={new_price}&cu=INR"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    bio = BytesIO()
    bio.name = "offer_qr.png"
    img.save(bio, "PNG")
    bio.seek(0)

    text = f"""
❌ *ORDER CANCELLED*

🔥 *SPECIAL OFFER*
💸 Old Price: ₹{store['price']}
⚡ Offer Price: ₹{new_price}

😄 Grab it now!
"""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 PROCEED PAYMENT", callback_data="buy"))
    kb.add(InlineKeyboardButton("⬅ BACK", callback_data="back"))

    bot.send_photo(c.message.chat.id, bio, caption=text, reply_markup=kb)


# =========================
# PAID → ADMIN
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(c):
    store = get_store()
    bot.answer_callback_query(c.id)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{c.from_user.id}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{c.from_user.id}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💰 *NEW PAYMENT*\n\nUser: `{c.from_user.id}`\nAmount: ₹{store['price']}",
        reply_markup=kb
    )

    bot.send_message(c.message.chat.id, "⏳ Sent for approval...")


# =========================
# APPROVE (SAFE)
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):
    user_id = int(c.data.split("_")[1])
    store = get_store()

    set_setting("sales", store["sales"] + 1)
    set_setting("revenue", store["revenue"] + int(store["price"]))

    bot.send_message(
        c.message.chat.id,
        "✅ APPROVED & LINK SENT\n💰 ₹29 Added to Stats."
    )

    bot.send_message(
        user_id,
        f"🎉 *Payment Approved!*\n\n🔗 {store['premium_link']}"
    )

    bot.answer_callback_query(c.id)


# =========================
# REJECT
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):
    user_id = int(c.data.split("_")[1])

    bot.send_message(user_id, "❌ Payment rejected")

    bot.send_message(c.message.chat.id, "❌ REJECTED")

    bot.answer_callback_query(c.id)


print("Bot running...")
bot.infinity_polling(skip_pending=True)
