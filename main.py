import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode
from io import BytesIO
import json
import os

from config import TOKEN, ADMIN_ID
from db import add_user, save_payment, get_payment, update_payment, get_all_users

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# LOAD DATA
def load_data():
    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            return json.load(f)
    else:
        return {
            "upi": "yourupi@bank",
            "demo": "",
            "price": "29",
            "name": "Premium Access",
            "premium_link": "",
            "start_text": "",
            "sales": 0,
            "revenue": 0,
            "photo": None
        }

store = load_data()
admin_wait = {}

def save_data():
    with open("data.json", "w") as f:
        json.dump(store, f)

def is_admin(uid):
    return uid == ADMIN_ID

def home_text():
    return f"*{store['name']}*\n\n{store['start_text']}\n\nPrice: Rs {store['price']}"

def home_markup():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Buy Premium", callback_data="buy"))
    kb.add(InlineKeyboardButton("Watch Demo", url=store["demo"]))
    return kb


@bot.message_handler(commands=["start"])
def start(message):
    add_user(message.chat.id)

    if store["photo"]:
        bot.send_photo(message.chat.id, store["photo"], caption=home_text(), reply_markup=home_markup())
    else:
        bot.send_message(message.chat.id, home_text(), reply_markup=home_markup())


@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(c):
    bot.answer_callback_query(c.id)

    upi_link = f"upi://pay?pa={store['upi']}&am={store['price']}&cu=INR"
    qr = qrcode.make(upi_link)

    bio = BytesIO()
    bio.name = 'qr.png'
    qr.save(bio, 'PNG')
    bio.seek(0)

    text = f"Pay Rs {store['price']} to `{store['upi']}`\n\nThen send screenshot."

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("I Have Paid", callback_data="paid"))

    bot.send_photo(c.message.chat.id, bio, caption=text, reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "Send payment screenshot now.")


@bot.message_handler(content_types=["photo"])
def payment_ss(message):

    if message.from_user.id == ADMIN_ID and admin_wait.get(message.from_user.id) == "photo":
        store["photo"] = message.photo[-1].file_id
        admin_wait.pop(message.from_user.id)
        save_data()
        bot.reply_to(message, "Photo updated ✅")
        return

    if message.from_user.id == ADMIN_ID:
        return

    caption = f"Payment Proof\nUser: {message.from_user.id}\nAmount: {store['price']}"

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Approve", callback_data="approve"),
        InlineKeyboardButton("Reject", callback_data="reject")
    )

    sent = bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=kb)

    save_payment(sent.message_id, message.from_user.id, "pending")

    bot.reply_to(message, "Screenshot sent to admin ✅")


@bot.callback_query_handler(func=lambda c: c.data == "approve")
def approve(c):
    data = get_payment(c.message.message_id)

    if not data:
        bot.answer_callback_query(c.id, "Not found")
        return

    msg_id, user_id, status = data

    if status == "approved":
        bot.answer_callback_query(c.id, "Already Approved ✅")
        return

    update_payment(msg_id, "approved")

    store["sales"] += 1
    store["revenue"] += int(store["price"])
    save_data()

    new_caption = c.message.caption + "\n\n✅ *APPROVED & LINK SENT*\n💰 Added"

    bot.edit_message_caption(chat_id=c.message.chat.id, message_id=msg_id, caption=new_caption)
    bot.edit_message_reply_markup(chat_id=c.message.chat.id, message_id=msg_id, reply_markup=None)

    bot.send_message(user_id, f"Payment Approved ✅\n\nLink:\n{store['premium_link']}")

    bot.answer_callback_query(c.id, "Approved")


@bot.callback_query_handler(func=lambda c: c.data == "reject")
def reject(c):
    data = get_payment(c.message.message_id)

    if not data:
        return

    _, user_id, _ = data
    bot.send_message(user_id, "Payment rejected ❌")
    bot.answer_callback_query(c.id, "Rejected")


# 🔥 FULL ADMIN PANEL
@bot.message_handler(commands=["admin"])
def admin(message):
    if not is_admin(message.from_user.id):
        return

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Set Price", callback_data="admin_price"),
        InlineKeyboardButton("Set UPI", callback_data="admin_upi")
    )
    kb.add(
        InlineKeyboardButton("Set Premium Link", callback_data="admin_link"),
        InlineKeyboardButton("Set Demo Link", callback_data="admin_demo")
    )
    kb.add(
        InlineKeyboardButton("Set Product Name", callback_data="admin_name"),
        InlineKeyboardButton("Set Start Text", callback_data="admin_starttext")
    )
    kb.add(
        InlineKeyboardButton("Set Photo", callback_data="admin_photo")
    )
    kb.add(
        InlineKeyboardButton("Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton("Stats", callback_data="admin_stats")
    )

    bot.send_message(message.chat.id, "Admin Controls", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_"))
def admin_btn(c):
    if not is_admin(c.from_user.id):
        return

    action = c.data.split("_", 1)[1]

    if action == "stats":
        users = get_all_users()
        bot.send_message(
            c.message.chat.id,
            f"Users: {len(users)}\nSales: {store['sales']}\nRevenue: Rs {store['revenue']}"
        )
        return

    if action == "photo":
        admin_wait[c.from_user.id] = "photo"
        bot.send_message(c.message.chat.id, "Photo bhejo 📸")
        return

    admin_wait[c.from_user.id] = action

    prompts = {
        "price": "Send new price",
        "upi": "Send new UPI",
        "link": "Send new premium link",
        "demo": "Send new demo link",
        "name": "Send new product name",
        "starttext": "Send new welcome text",
        "broadcast": "Send message to broadcast"
    }

    bot.send_message(c.message.chat.id, prompts[action])


@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.from_user.id in admin_wait)
def admin_input(message):
    action = admin_wait.pop(message.from_user.id)

    if action == "price":
        store["price"] = message.text.strip()

    elif action == "upi":
        store["upi"] = message.text.strip()

    elif action == "link":
        store["premium_link"] = message.text.strip()

    elif action == "demo":
        store["demo"] = message.text.strip()

    elif action == "name":
        store["name"] = message.text.strip()

    elif action == "starttext":
        store["start_text"] = message.text.strip()

    elif action == "broadcast":
        sent = 0
        for user in get_all_users():
            try:
                bot.send_message(user[0], message.text)
                sent += 1
            except:
                pass
        bot.reply_to(message, f"Broadcast sent to {sent} users")
        return

    save_data()
    bot.reply_to(message, "Updated successfully ✅")


print("Bot running...")
bot.infinity_polling(skip_pending=True)
