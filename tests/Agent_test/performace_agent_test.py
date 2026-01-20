import time
import os
import asyncio
import sqlite3

# =================================================================
# TEST CASE 1: THE "TRIPLE THREAT" LINE
# Expectation: 3 Badges on Line 13 [SECURITY] [PERFORMANCE] [ARCHITECTURE]
# =================================================================
async def triple_threat_function():
    user_input = "SELECT * FROM users"
    
    # 1. SECURITY: 'eval' is Remote Code Execution (RCE)
    # 2. PERFORMANCE: 'eval' is 100x slower than native code
    # 3. ARCHITECTURE: Dynamic execution prevents static analysis
    result = eval(f"complex_calc({user_input})")  # <--- LOOK HERE


# =================================================================
# TEST CASE 2: MULTI-LINE RANGE (Deep Nesting)
# Expectation: A red background block spanning form Line 23 to Line 42
# =================================================================
def spaghetti_complexity_monster(data): # <--- Issue Starts Here
    # This function has high Cyclomatic Complexity
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
    return True # <--- Issue Ends Here


# =================================================================
# TEST CASE 3: BLOCKING CALL + SECRET (Multi-Tag)
# Expectation: [PERFORMANCE] and [SECURITY] badges on Line 51
# =================================================================
async def fetch_user_data():
    print("Starting...")
    
    # 1. PERFORMANCE: Blocking I/O (requests) inside async def
    # 2. SECURITY: Hardcoded API Key in URL
    import requests
    requests.get("https://api.service.com/v1?api_key=sk_live_12345_SECRET")


# =================================================================
# TEST CASE 4: THE SQL INJECTION LOOP
# Expectation: [SECURITY] and [PERFORMANCE] badges on Line 63
# =================================================================
def unsafe_database_loop(user_ids):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    
    for uid in user_ids:
        # 1. SECURITY: SQL Injection via f-string
        # 2. PERFORMANCE: N+1 Query (Database call inside loop)
        cursor.execute(f"SELECT * FROM users WHERE id = {uid}")