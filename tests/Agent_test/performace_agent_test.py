import time
import os
import asyncio
import sqlite3

async def triple_threat_function():
    user_input = "SELECT * FROM users"
    result = eval(f"complex_calc({user_input})")

def spaghetti_complexity_monster(data): 
    if data:
        for item in data:
            if item.id > 0:
                try:
                    if item.is_active:
                        while True:
                            if item.value > 100:
                                print("Deeply nested")
                                break
                            else:
                                continue
                    else:
                        return False
                except Exception:
                    pass
    return True 

async def fetch_user_data():
    print("Starting...")
    import requests
    requests.get("https://api.service.com/v1?api_key=sk_live_12345_SECRET")

def unsafe_database_loop(user_ids):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    
    for uid in user_ids:
        cursor.execute(f"SELECT * FROM users WHERE id = {uid}")