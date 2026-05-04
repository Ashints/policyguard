import os 
from datetime import datetime, timedelta
from jose import jwt, JWTError
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET is not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(user_id: str,role: str="user") ->str:
    expire=datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload={
        "sub":user_id,
        "role":role,
        "exp":expire,
        "iat":datetime.utcnow()
    }
    return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)

def decode_access_token(token:str) -> dict | None:
    try:
        payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        user_id=payload.get('sub')
        if not user_id:
            return None
        return payload
    except JWTError:
        return None