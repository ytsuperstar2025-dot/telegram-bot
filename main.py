import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode
from io import BytesIO

from config import TOKEN, ADMIN_ID
from db import add_user, set_setting, get_setting, get_all_users

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

admin_wait = {}
offer_price = {}
pending_screenshot = {}


# =========================
# STORE
# =========================
def get_store():
    return {
        "upi": get_setting("upi", ""),
        "demo": get_setting("demo", ""),
        "price": get_setting("price", "0"),
        "name": get_setting("name", ""),
        "premium_link": get_setting("premium_link", ""),
        "start_text": get_setting("start_text", ""),
        "photo": get_setting("photo", None),
        "sales": int(get_setting("sales", "0")),
        "revenue": int(get_setting("revenue", "0")),
    }


# =========================
# PAYMENT TEXT
# =========================
def payment_text(store, price):
    return f"""

⚡ 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐆𝐀𝐓𝐄𝐖𝐀𝐘

📛 𝐀𝐜𝐜𝐞𝐬𝐬: {store['name'] or "Not Set"}
💵 𝐀𝐦𝐨𝐮𝐧𝐭: ₹{price}
🏦 𝐔𝐏𝐈 𝐈𝐃: `{store['upi'] or "Not Set"}`

1️⃣ 𝐒𝐜𝐚𝐧 𝐐𝐑 𝐂𝐨𝐝𝐞
2️⃣ 𝐏𝐚𝐲 𝐮𝐬𝐢𝐧𝐠 𝐔𝐏𝐈
3️⃣ 𝐂𝐥𝐢𝐜𝐤 𝐛𝐮𝐭𝐭𝐨𝐧 𝐛𝐞𝐥𝐨𝐰

📸 Send screenshot after payment
"""


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    store = get_store()
    add_user(message.chat.id)

    custom = store["start_text"]

    if custom:
        text = custom
    else:
        text = "Welcome!"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 BUY PREMIUM", callback_data="buy"))
    kb.add(InlineKeyboardButton("🎬 DEMO", url=store["demo"]))

    photo = store.get("photo")

    if photo:
        try:
            bot.send_photo(message.chat.id, photo, caption=text, reply_markup=kb)
        except:
            bot.send_message(message.chat.id, text, reply_markup=kb)
    else:
        bot.send_message(message.chat.id, text, reply_markup=kb)


# =========================
# ADMIN PANEL
# =========================
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if int(message.chat.id) != int(ADMIN_ID):
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
# ADMIN SET
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_set(c):
    if int(c.from_user.id) != int(ADMIN_ID):
        return

    admin_wait[c.from_user.id] = c.data.replace("set_", "")
    bot.send_message(c.message.chat.id, "✏ Send value now:")


# =========================
# MESSAGE HANDLER (ADMIN + SCREENSHOT)
# =========================
@bot.message_handler(content_types=['text', 'photo'])
def handle_all(m):

    user_id = m.from_user.id

    # ================= ADMIN UPDATE =================
    if user_id in admin_wait:
        action = admin_wait[user_id]

        if action == "photo":
            if m.photo:
                set_setting("photo", m.photo[-1].file_id)
                bot.send_message(m.chat.id, "🖼 PHOTO UPDATED")
            admin_wait.pop(user_id, None)
            return

        if m.text:
            set_setting(action, m.text)
            bot.send_message(m.chat.id, "✅ UPDATED")

        admin_wait.pop(user_id, None)
        return

    # ================= SCREENSHOT FLOW =================
    if pending_screenshot.get(user_id):

        if not m.photo:
            bot.send_message(m.chat.id, "📸 Please send a valid screenshot image.")
            return

        pending_screenshot.pop(user_id, None)
        store = get_store()

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}")
        )

        bot.send_photo(
            ADMIN_ID,
            m.photo[-1].file_id,
            caption=f"💰 PAYMENT PROOF\nUser: {user_id}",
            reply_markup=kb
        )

        bot.send_message(
            m.chat.id,
            "✅ Screenshot received!\n⏳ Verification in progress...\n🔗 Access will be sent soon."
        )


# =========================
# BUY
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(c):
    store = get_store()

    price = offer_price.get(c.from_user.id, int(store["price"]))

    qr_link = f"upi://pay?pa={store['upi']}&am={price}&cu=INR"

    qr = qrcode.QRCode()
    qr.add_data(qr_link)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 I HAVE PAID", callback_data="paid"))
    kb.add(InlineKeyboardButton("❌ CANCEL ORDER", callback_data="cancel"))

    bot.send_photo(c.message.chat.id, bio, caption=payment_text(store, price), reply_markup=kb)


# =========================
# PAID BUTTON
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(c):
    pending_screenshot[c.from_user.id] = True

    bot.send_message(
        c.message.chat.id,
        "📸 Please send your <b>payment screenshot</b> here."
    )


# =========================
# CANCEL
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(c):
    store = get_store()

    old_price = int(store["price"])
    new_price = max(1, old_price - 2)

    offer_price[c.from_user.id] = new_price

    qr_link = f"upi://pay?pa={store['upi']}&am={new_price}&cu=INR"

    qr = qrcode.QRCode()
    qr.add_data(qr_link)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)

    # 🔥 PRO HIGH-CONVERTING TEXT
    text = f"""
    ❌ <b>ORDER CANCELLED</b>

    😔 Miss ho gaya...

    🔥 <b>EXCLUSIVE DEAL UNLOCKED</b>

     ━━━━━━━━━━━━━━━
    💰 <s>₹{old_price}</s> ❌
    🎉 <b>Now Only:</b> ₹{new_price} ✅
     ━━━━━━━━━━━━━━━

    ⏳ <b>Only few users can grab this deal</b>
    ⚡ <b>Instant Access</b>
    🔐 <b>Private Premium Content</b>

    🚨 <b>Hurry! Offer may expire anytime</b>

    👇 <b>Tap below to grab now</b>
"""

    # 🔥 PRO BUTTON
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔥 LIMITED OFFER - GRAB NOW", callback_data="buy"))

    bot.send_photo(c.message.chat.id, bio, caption=text, reply_markup=kb)


# =========================
# APPROVE / REJECT (FIXED)
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):
    user_id = int(c.data.split("_")[1])
    store = get_store()

    set_setting("sales", str(int(store["sales"]) + 1))
    set_setting("revenue", str(int(store["revenue"]) + int(store["price"])))

    offer_price.pop(user_id, None)

    bot.send_message(c.message.chat.id, "✅ APPROVED & LINK SENT")
    
    bot.send_message(
    user_id,
    f"""🎉 *APPROVED!*

🔥 *Access Granted Successfully*

👇 *Join Here:*
{store["premium_link"]}

⚠️ Request to join, approval instantly milega."""
)


@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):
    user_id = int(c.data.split("_")[1])

    offer_price.pop(user_id, None)

    bot.send_message(c.message.chat.id, "❌ REJECTED")
    bot.send_message(user_id, "❌ Payment rejected")


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
