import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode
from io import BytesIO

from config import TOKEN, ADMIN_ID
from db import add_user, set_setting, get_setting, get_all_users

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

admin_wait = {}


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
        "photo": get_setting("photo", None),
        "sales": int(get_setting("sales", "0")),
        "revenue": int(get_setting("revenue", "0")),
    }


# =========================
# HOME TEXT
# =========================
def home_text(store):
    return f"""
⚡ *PAYMENT GATEWAY*

📛 *Access:* {store['name']}
💵 *Amount:* ₹{store['price']}
🏦 *UPI:* `{store['upi']}`
"""


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    store = get_store()
    add_user(message.chat.id)

    text = store["start_text"] if store["start_text"] else home_text(store)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 BUY PREMIUM", callback_data="buy"))
    kb.add(InlineKeyboardButton("🎬 DEMO", url=store["demo"]))

    if store["photo"]:
        bot.send_photo(message.chat.id, store["photo"], caption=text, reply_markup=kb)
    else:
        bot.send_message(message.chat.id, text, reply_markup=kb)


# =========================
# ADMIN PANEL
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

    kb.add(InlineKeyboardButton("📣 BROADCAST", callback_data="broadcast"))
    kb.add(InlineKeyboardButton("👥 USERS", callback_data="users"))
    kb.add(InlineKeyboardButton("📊 STATS", callback_data="stats"))

    bot.send_message(message.chat.id, "👑 *ADMIN PANEL*", reply_markup=kb)


# =========================
# BUY
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(c):
    store = get_store()

    price = int(store["price"])
    upi = store["upi"]

    qr_link = f"upi://pay?pa={upi}&am={price}&cu=INR"

    qr = qrcode.QRCode()
    qr.add_data(qr_link)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💳 I HAVE PAID", callback_data="paid"))
    kb.add(InlineKeyboardButton("❌ CANCEL ORDER", callback_data="cancel"))
    kb.add(InlineKeyboardButton("⬅ BACK", callback_data="back"))

    bot.send_photo(c.message.chat.id, bio, caption=home_text(store), reply_markup=kb)


# =========================
# CANCEL ORDER
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(c):
    store = get_store()

    old_price = int(store["price"])
    new_price = max(1, old_price - 2)

    qr_link = f"upi://pay?pa={store['upi']}&am={new_price}&cu=INR"

    qr = qrcode.QRCode()
    qr.add_data(qr_link)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)

    text = f"""
❌ *ORDER CANCELLED*

🔥 *SPECIAL OFFER*
💰 Old Price: ₹{old_price}
🎯 Discount: ₹2 OFF
💸 New Price: ₹{new_price}
"""

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💳 PAY NOW", callback_data="buy"))
    kb.add(InlineKeyboardButton("⬅ BACK", callback_data="back"))

    bot.send_photo(c.message.chat.id, bio, caption=text, reply_markup=kb)


# =========================
# PAID → ADMIN
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(c):
    store = get_store()

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{c.from_user.id}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{c.from_user.id}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💰 PAYMENT REQUEST\nUser: {c.from_user.id}",
        reply_markup=kb
    )

    bot.send_message(c.message.chat.id, "📤 Sent to admin")


# =========================
# APPROVE
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):
    user_id = int(c.data.split("_")[1])
    store = get_store()

    set_setting("sales", str(store["sales"] + 1))
    set_setting("revenue", str(store["revenue"] + int(store["price"])))

    bot.edit_message_text("✅ APPROVED & LINK SENT", c.message.chat.id, c.message.message_id)

    bot.send_message(user_id, f"🎉 Approved!\n\n🔗 {store['premium_link']}")


# =========================
# REJECT
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):
    user_id = int(c.data.split("_")[1])

    bot.send_message(user_id, "❌ Payment Rejected")
    bot.edit_message_text("❌ REJECTED", c.message.chat.id, c.message.message_id)


# =========================
# USERS
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "users")
def users(c):
    users = get_all_users()
    bot.send_message(c.message.chat.id, f"👥 TOTAL USERS: {len(users)}")


# =========================
# STATS
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(c):
    store = get_store()
    bot.send_message(
        c.message.chat.id,
        f"📊 SALES: {store['sales']}\n💰 REVENUE: ₹{store['revenue']}"
    )


# =========================
# ADMIN INPUT SYSTEM (FIX)
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_set(c):
    if c.from_user.id != ADMIN_ID:
        return

    admin_wait[c.from_user.id] = c.data.replace("set_", "")
    bot.send_message(c.message.chat.id, "✏ Send value now:")


@bot.message_handler(func=lambda m: m.from_user.id in admin_wait)
def save_admin(m):
    action = admin_wait[m.from_user.id]

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

    elif action == "photo":
        set_setting("photo", m.photo[-1].file_id)

    del admin_wait[m.from_user.id]
    bot.send_message(m.chat.id, "✅ UPDATED SUCCESSFULLY!")


print("Bot Running...")
bot.infinity_polling(skip_pending=True)
