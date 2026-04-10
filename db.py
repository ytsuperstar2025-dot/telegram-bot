from pymongo import MongoClient
import os

client = MongoClient(os.getenv("MONGO_URL"))
db = client["telegram_bot"]

users_col = db["users"]
payments_col = db["payments"]
settings_col = db["settings"]

# USERS
def add_user(uid):
    users_col.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)

def get_all_users():
    return list(users_col.find({}, {"_id": 0, "user_id": 1}))

# PAYMENTS
def save_payment(msg_id, user_id, status):
    payments_col.insert_one({
        "msg_id": msg_id,
        "user_id": user_id,
        "status": status
    })

def get_payment(msg_id):
    return payments_col.find_one({"msg_id": msg_id})

def update_payment(msg_id, status):
    payments_col.update_one({"msg_id": msg_id}, {"$set": {"status": status}})

# SETTINGS
def set_setting(key, value):
    settings_col.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

def get_setting(key, default=None):
    data = settings_col.find_one({"key": key})
    return data["value"] if data else default
