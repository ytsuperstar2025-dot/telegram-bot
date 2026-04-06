import os

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if TOKEN is None:
    raise ValueError("TOKEN environment variable missing!")

if ADMIN_ID is None:
    raise ValueError("ADMIN_ID environment variable missing!")

ADMIN_ID = int(ADMIN_ID)
