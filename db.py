import sqlite3

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

# USERS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

# PAYMENTS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS payments (
    msg_id INTEGER,
    user_id INTEGER,
    status TEXT
)
""")

# SETTINGS TABLE (IMPORTANT 🔥)
cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

conn.commit()

# -------- USERS --------
def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    conn.commit()

def get_all_users():
    return cur.execute("SELECT user_id FROM users").fetchall()


# -------- PAYMENTS --------
def save_payment(msg_id, user_id, status):
    cur.execute("INSERT INTO payments VALUES (?, ?, ?)", (msg_id, user_id, status))
    conn.commit()

def get_payment(msg_id):
    return cur.execute("SELECT msg_id, user_id, status FROM payments WHERE msg_id=?", (msg_id,)).fetchone()

def update_payment(msg_id, status):
    cur.execute("UPDATE payments SET status=? WHERE msg_id=?", (status, msg_id))
    conn.commit()


# -------- SETTINGS (🔥 MAIN FIX) --------
def set_setting(key, value):
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

def get_setting(key, default=None):
    res = cur.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return res[0] if res else default
