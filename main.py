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
# ADMIN PANEL (RESTORED)
# =========================
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        return

    store = get_store()

    text = f"""
🛠 *ADMIN PANEL*

📦 Product: {store['name']}
💰 Price: ₹{store['price']}
🏦 UPI: `{store['upi']}`
🔗 Link: {store['premium_link']}
"""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✏ Set Price", callback_data="set_price"))
    kb.add(InlineKeyboardButton("✏ Set UPI", callback_data="set_upi"))
    kb.add(InlineKeyboardButton("✏ Set Name", callback_data="set_name"))
    kb.add(InlineKeyboardButton("✏ Set Link", callback_data="set_link"))

    bot.send_message(message.chat.id, text, reply_markup=kb)


# =========================
# ADMIN SET VALUE FLOW
# =========================
admin_wait = {}


@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def set_value(c):
    if c.from_user.id != ADMIN_ID:
        return

    key = c.data.replace("set_", "")
    admin_wait[ADMIN_ID] = key

    bot.send_message(c.message.chat.id, f"✏ Send new value for *{key}*")


@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def admin_input(message):
    if ADMIN_ID not in admin_wait:
        return

    key = admin_wait[ADMIN_ID]
    value = message.text

    set_setting(key, value)
    admin_wait.pop(ADMIN_ID)

    bot.send_message(message.chat.id, f"✅ Updated *{key}* = {value}")


# =========================
# START
# =========================
def home_text(store):
    return f"*{store['name']}*\n\n{store['start_text']}\n\nPrice: ₹{store['price']}"


def home_markup(store):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Buy Premium", callback_data="buy"))
    kb.add(InlineKeyboardButton("🎬 Watch Demo", url=store["demo"]))
    return kb


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
# BUY PAGE
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
⚡ *𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐆𝐀𝐓𝐄𝐖𝐀𝐘*

📦 *𝐀𝐜𝐜𝐞𝐬𝐬:* {store['name']}
💰 *𝐏𝐫𝐢𝐜𝐞:* ₹{store['price']}

1️⃣ 𝐒𝐜𝐚𝐧 𝐐𝐑 𝐂𝐨𝐝𝐞  
2️⃣ 𝐏𝐚𝐲 𝐮𝐬𝐢𝐧𝐠 𝐔𝐏𝐈  
3️⃣ 𝐂𝐥𝐢𝐜𝐤 𝐛𝐞𝐥𝐨𝐰  
"""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 I HAVE PAID", callback_data="paid"))
    kb.add(InlineKeyboardButton("❌ CANCEL ORDER", callback_data="cancel"))
    kb.add(InlineKeyboardButton("⬅ BACK", callback_data="back"))

    bot.send_photo(c.message.chat.id, bio, caption=caption, reply_markup=kb)


# =========================
# CANCEL OFFER
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(c):
    store = get_store()
    bot.answer_callback_query(c.id)

    old = int(store["price"])
    new = max(1, old - 2)

    upi_link = f"upi://pay?pa={store['upi']}&am={new}&cu=INR"

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
    bio.name = "offer.png"
    img.save(bio, "PNG")
    bio.seek(0)

    text = f"""
❌ *ORDER CANCELLED*

🔥 SPECIAL OFFER
💸 Old: ₹{old}
⚡ New: ₹{new}
"""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 PROCEED", callback_data="buy"))
    kb.add(InlineKeyboardButton("⬅ BACK", callback_data="back"))

    bot.send_photo(c.message.chat.id, bio, caption=text, reply_markup=kb)


# =========================
# PAID
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "📸 Send screenshot for approval")


# =========================
# SCREENSHOT TO ADMIN
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
        caption=f"💰 PAYMENT\nUser: `{message.from_user.id}`\n₹{store['price']}",
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

    bot.send_message(user_id, f"🎉 Approved!\n\n🔗 {store['premium_link']}")
    bot.send_message(c.message.chat.id, "✅ APPROVED")

    bot.answer_callback_query(c.id)


# =========================
# REJECT
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):
    user_id = int(c.data.split("_")[1])

    bot.send_message(user_id, "❌ Rejected")
    bot.send_message(c.message.chat.id, "❌ REJECTED")

    bot.answer_callback_query(c.id)


print("Bot running...")
bot.infinity_polling(skip_pending=True)
