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
        InlineKeyboardButton("Approve", callback_data=f"approve"),
        InlineKeyboardButton("Reject", callback_data=f"reject")
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


@bot.message_handler(commands=["admin"])
def admin(message):
    if not is_admin(message.from_user.id):
        return

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Stats", callback_data="stats"))
    bot.send_message(message.chat.id, "Admin Panel", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(c):
    users = get_all_users()
    bot.send_message(c.message.chat.id, f"Users: {len(users)}\nSales: {store['sales']}\nRevenue: Rs {store['revenue']}")


print("Bot running...")
bot.infinity_polling()
