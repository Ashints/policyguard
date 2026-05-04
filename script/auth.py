import os 
import time
from collections import defaultdict
from fastapi import Header,Depends, HTTPException
from script.jwt_auth import get_current_user


APP_API_KEY = os.getenv("APP_API_KEY")

RATE_LIMIT = 5     
WINDOW_SECONDS = 60  
request_store = defaultdict(list)

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != APP_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    
def rate_limit(payload: dict = Depends(get_current_user)):
    user_id=payload["sub"]
    now = time.time()
    window_start = now - WINDOW_SECONDS    

    if user_id not in request_store:
        request_store[user_id] = []

    request_store[user_id] = [
        t for t in request_store[user_id]
        if t > window_start
    ]

    # check limit
    if len(request_store[user_id]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )

    # record request
    request_store[user_id].append(now)