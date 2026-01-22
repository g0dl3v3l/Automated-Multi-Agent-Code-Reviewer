import asyncio
import re
import math
import random
from typing import List, Dict, Any

GLOBAL_METRICS = []
SHARED_RESOURCE_COUNTER = 0

async def monitor_system_metrics():
    while True:
        metric = {"timestamp": asyncio.get_event_loop().time(), "value": random.randint(1, 100)}
        GLOBAL_METRICS.append(metric)
        await asyncio.sleep(1)

def validate_and_parse_logs(log_lines: List[str]) -> List[Dict[str, Any]]:
    parsed_data = []
    for line in log_lines:
        log_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}) \[(.*?)\] (.*)$")
        match = log_pattern.match(line)
        if match:
            parsed_data.append({
                "date": match.group(1),
                "level": match.group(2),
                "message": match.group(3)
            })
    return parsed_data

async def handle_prime_calculation_request(n: int):
    result = _calculate_nth_prime(n)
    return {"status": "done", "result": result}

def _calculate_nth_prime(n: int):
    count = 0
    num = 2
    while count < n:
        if all(num % i != 0 for i in range(2, int(math.sqrt(num)) + 1)):
            count += 1
        num += 1
    return num - 1

async def unsafe_counter_update():
    global SHARED_RESOURCE_COUNTER
    current_value = SHARED_RESOURCE_COUNTER
    await asyncio.sleep(0.01)
    SHARED_RESOURCE_COUNTER = current_value + 1

async def run_concurrent_updates():
    tasks = [unsafe_counter_update() for _ in range(100)]
    await asyncio.gather(*tasks)

def process_full_order_lifecycle(
    order_id: str,
    user_id: str,
    items: List[Dict],
    payment_method: str,
    shipping_address: Dict,
    billing_address: Dict,
    discount_code: str = None,
    gift_wrap: bool = False,
    notes: str = ""
):
    if not order_id or not user_id:
        return {"error": "Invalid IDs"}
    
    total_price = 0
    valid_items = []
    for item in items:
        if item['quantity'] > 0 and item['price'] >= 0:
            valid_items.append(item)
            total_price += item['quantity'] * item['price']
    
    if discount_code:
        if discount_code == "SUMMER20":
            total_price *= 0.8
        elif discount_code == "WELCOME10":
            total_price *= 0.9
            
    tax_rate = 0.0
    if shipping_address.get('country') == 'US':
        state = shipping_address.get('state')
        if state == 'CA':
            tax_rate = 0.0725
        elif state == 'NY':
            tax_rate = 0.04
    elif shipping_address.get('country') == 'UK':
        tax_rate = 0.20
        
    final_total = total_price * (1 + tax_rate)
    
    payment_status = "pending"
    if payment_method == "credit_card":
        if len(billing_address.get('zip', '')) == 5:
            payment_status = "authorized"
        else:
            payment_status = "failed"
    elif payment_method == "paypal":
        payment_status = "authorized"
        
    shipping_label = None
    if payment_status == "authorized":
        weight = sum(i.get('weight', 0) for i in items)
        if weight < 10:
            cost = 5.00
        else:
            cost = 15.00
        shipping_label = f"SHIP-{order_id}-{cost}"
        
        email_body = f"Order {order_id} confirmed. Total: {final_total}"
        if gift_wrap:
            email_body += " (Gift Wrapped)"
            
    return {
        "order_id": order_id,
        "status": "processed" if payment_status == "authorized" else "failed",
        "total": final_total,
        "shipping_label": shipping_label
    }