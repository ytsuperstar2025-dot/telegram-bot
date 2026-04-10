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
# STORE
# =========================
def get_store():
    return {
        "upi": get_setting("upi", ""),
        "demo": get_setting("demo", ""),
        "price": get_setting("price", ""),
        "name": get_setting("name", ""),
        "premium_link": get_setting("premium_link", ""),
        "start_text": get_setting("start_text", ""),
        "photo": get_setting("photo", ""),
        "sales": int(get_setting("sales", "0")),
        "revenue": int(get_setting("revenue", "0")),
    }


# =========================
# START (PHOTO FIXED 100%)
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

    # ✅ FIXED SAFE PHOTO CHECK + TRY CATCH
    if photo and photo != "" and photo != "None":
        try:
            bot.send_photo(message.chat.id, photo, caption=text, reply_markup=kb)
        except:
            bot.send_message(message.chat.id, text, reply_markup=kb)
    else:
        bot.send_message(message.chat.id, text, reply_markup=kb)


# =========================
# ADMIN PHOTO FIX
# =========================
@bot.message_handler(func=lambda m: m.from_user.id in admin_wait)
def save_admin(m):
    action = admin_wait[m.from_user.id]

    if action == "photo":
        if m.photo:
            set_setting("photo", m.photo[-1].file_id)
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


# =========================
# BUY
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(c):
    store = get_store()
    user_id = c.from_user.id

    price = offer_price.get(user_id, int(store["price"] or 0))

    qr_link = f"upi://pay?pa={store['upi']}&am={price}&cu=INR"

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

    bot.send_photo(c.message.chat.id, bio, caption="⚡ ORDER", reply_markup=kb)


# =========================
# CANCEL (OFFER)
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(c):
    store = get_store()
    user_id = c.from_user.id

    old_price = int(store["price"] or 0)
    new_price = max(1, old_price - 2)

    offer_price[user_id] = new_price

    qr_link = f"upi://pay?pa={store['upi']}&am={new_price}&cu=INR"

    qr = qrcode.QRCode()
    qr.add_data(qr_link)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)

    text = f"❌ ORDER CANCELLED\n🔥 OFFER ACTIVE ₹{new_price}"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 PAY NOW", callback_data="buy"))

    bot.send_photo(c.message.chat.id, bio, caption=text, reply_markup=kb)


# =========================
# PAID
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(c):
    store = get_store()

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{c.from_user.id}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{c.from_user.id}")
    )

    bot.send_message(ADMIN_ID, f"💰 PAYMENT\nUser: {c.from_user.id}", reply_markup=kb)
    bot.send_message(c.message.chat.id, "📤 SENT")


# =========================
# APPROVE
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):
    user_id = int(c.data.split("_")[1])
    store = get_store()

    set_setting("sales", str(store["sales"] + 1))
    set_setting("revenue", str(store["revenue"] + int(store["price"] or 0)))

    offer_price.pop(user_id, None)

    bot.edit_message_text("✅ APPROVED & LINK SENT", c.message.chat.id, c.message.message_id)
    bot.send_message(user_id, store["premium_link"])


# =========================
# REJECT
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):
    user_id = int(c.data.split("_")[1])

    offer_price.pop(user_id, None)

    bot.send_message(user_id, "❌ REJECTED")
    bot.edit_message_text("❌ REJECTED", c.message.chat.id, c.message.message_id)


# =========================
# USERS / STATS
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "users")
def users(c):
    users = get_all_users()
    bot.send_message(c.message.chat.id, f"👥 USERS: {len(users)}")


@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(c):
    store = get_store()
    bot.send_message(c.message.chat.id, f"📊 SALES: {store['sales']}\n💰 REVENUE: ₹{store['revenue']}")


print("Bot Running...")
bot.infinity_polling(skip_pending=True)
