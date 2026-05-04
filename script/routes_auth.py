from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime
from pymongo.errors import DuplicateKeyError

from script.db import users_collection
from script.security import hash_password, verify_password
from script.jwt import create_access_token
from dotenv import load_dotenv

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(req: RegisterRequest):
    try:    
        users_collection.insert_one({
            "email":req.email,
            "password_hash":hash_password(req.password),
            "role":"user",
            "created_at": datetime.utcnow(),
            "is_active":True
        })
    except DuplicateKeyError:
        raise HTTPException(status_code=400,detail="user already exists") 
    
    return {"message":"User registred successfully"}

@router.post("/login")
def login(req:LoginRequest):
    user=users_collection.find_one({"email":req.email})

    fake_hash = "$2b$12$C6UzMDM.H6dfI/f/IKcEe."
    password_hash = user["password_hash"] if user else fake_hash

    if not verify_password(req.password,password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user or not user.get("is_active", False):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token=create_access_token(user_id=str(user["_id"]),
    role=user["role"])

    return{
        "access_token":token,
        "token_type":"bearer",
        "role": user["role"]  
    }