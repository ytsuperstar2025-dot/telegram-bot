import sqlite3

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    message_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    status TEXT
)
""")

conn.commit()

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()

def save_payment(message_id, user_id, status):
    cursor.execute("INSERT OR REPLACE INTO payments VALUES (?, ?, ?)", (message_id, user_id, status))
    conn.commit()

def get_payment(message_id):
    return cursor.execute("SELECT * FROM payments WHERE message_id=?", (message_id,)).fetchone()

def update_payment(message_id, status):
    cursor.execute("UPDATE payments SET status=? WHERE message_id=?", (status, message_id))
    conn.commit()

def get_all_users():
    return cursor.execute("SELECT user_id FROM users").fetchall()
