# script/bootstrap_admin.py
import os
from script.db import users_collection
from script.security import hash_password

def bootstrap_admin():
    email = os.getenv("INITIAL_ADMIN_EMAIL")
    password = os.getenv("INITIAL_ADMIN_PASSWORD")

    if not email or not password:
        return  # nothing to do

    if users_collection.find_one({"email": email}):
        return  # admin already exists

    users_collection.insert_one({
        "email": email,
        "password_hash": hash_password(password),
        "role": "admin",
        "is_active": True
    })

    print("Initial admin account created")
