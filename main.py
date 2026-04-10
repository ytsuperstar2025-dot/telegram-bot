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
        "start_text": get_setting("start_text", "")
    }


# =========================
# START TEXT (FIXED)
# =========================
def home_text(store):
    text = store.get("start_text")
    if text and text.strip():
        return text

    return f"*{store['name']}*\n\nPrice: ₹{store['price']}"


def home_markup(store):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 BUY PREMIUM", callback_data="buy"))
    kb.add(InlineKeyboardButton("🎬 WATCH DEMO", url=store["demo"]))
    return kb


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    store = get_store()
    add_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        home_text(store),
        reply_markup=home_markup(store)
    )


# =========================
# BACK
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(c):
    store = get_store()
    bot.answer_callback_query(c.id)

    bot.send_message(
        c.message.chat.id,
        home_text(store),
        reply_markup=home_markup(store)
    )


# =========================
# BUY (QR + UI FIXED)
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(c):
    store = get_store()
    bot.answer_callback_query(c.id)

    upi_link = f"upi://pay?pa={store['upi']}&am={store['price']}&cu=INR"

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

    caption = f"""
⚡ *PAYMENT GATEWAY*

📦 *Access:* {store['name']}
💰 *Price:* ₹{store['price']}

1️⃣ Scan QR Code  
2️⃣ Pay using UPI  
3️⃣ Click button below  
"""

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔥💳 I HAVE PAID", callback_data="paid"))
    kb.add(InlineKeyboardButton("❌ CANCEL ORDER", callback_data="cancel"))
    kb.add(InlineKeyboardButton("⬅ BACK", callback_data="back"))

    bot.send_photo(c.message.chat.id, bio, caption=caption, reply_markup=kb)


# =========================
# CANCEL ORDER (₹2 OFF OFFER)
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel_order(c):
    store = get_store()
    bot.answer_callback_query(c.id)

    old_price = int(store["price"])
    new_price = max(1, old_price - 2)

    upi_link = f"upi://pay?pa={store['upi']}&am={new_price}&cu=INR"

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
💸 Old Price: ₹{old_price}
⚡ Offer Price: ₹{new_price}

😄 Where are you going?
"""

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💳 PROCEED PAYMENT", callback_data="buy"))
    kb.add(InlineKeyboardButton("⬅ BACK", callback_data="back"))

    bot.send_photo(c.message.chat.id, bio, caption=text, reply_markup=kb)


# =========================
# PAID → ASK SCREENSHOT
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(c):
    bot.answer_callback_query(c.id)

    bot.send_message(
        c.message.chat.id,
        "📸 Send your payment screenshot for approval"
    )


# =========================
# SCREENSHOT → ADMIN
# =========================
@bot.message_handler(content_types=["photo"])
def screenshot(message):
    if message.from_user.id == ADMIN_ID:
        return

    store = get_store()

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{message.from_user.id}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{message.from_user.id}")
    )

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=f"""
💰 *PAYMENT PROOF*

👤 User: `{message.from_user.id}`
💵 Amount: ₹{store['price']}
""",
        reply_markup=kb
    )

    bot.reply_to(message, "📤 Sent to admin")


# =========================
# APPROVE
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):
    user_id = int(c.data.split("_")[1])
    store = get_store()

    set_setting("sales", str(int(get_setting("sales", "0")) + 1))
    set_setting("revenue", str(int(get_setting("revenue", "0")) + int(store["price"])))

    bot.send_message(c.message.chat.id, "✅ APPROVED")
    bot.send_message(user_id, f"🎉 Payment Approved!\n\n🔗 {store['premium_link']}")

    bot.answer_callback_query(c.id)


# =========================
# REJECT
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):
    user_id = int(c.data.split("_")[1])

    bot.send_message(user_id, "❌ Payment Rejected")
    bot.send_message(c.message.chat.id, "❌ REJECTED")

    bot.answer_callback_query(c.id)


print("Bot running...")
bot.infinity_polling(skip_pending=True)
