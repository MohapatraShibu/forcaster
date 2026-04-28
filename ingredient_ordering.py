"""
given predicted total covers for a day, calculates how much of each ingredient
to order, accounting for:
- Usage per cover (recipe yield)
- Current stock on hand
- Shelf life (don't over-order perishables)
- Supplier lead time (order must arrive before needed)

ingredient catalogue is stored in data/ingredients.json
current stock is stored in data/stock.json
"""

import json
import os
from datetime import date, timedelta

INGREDIENTS_FILE = "data/ingredients.json"
STOCK_FILE = "data/stock.json"

# default ingredient catalogue
DEFAULT_INGREDIENTS = {
    "chicken_breast":  {"unit": "kg",  "per_cover": 0.18, "shelf_life_days": 3,  "lead_time_days": 1, "safety_stock": 2.0},
    "beef_mince":      {"unit": "kg",  "per_cover": 0.12, "shelf_life_days": 2,  "lead_time_days": 1, "safety_stock": 1.5},
    "salmon_fillet":   {"unit": "kg",  "per_cover": 0.15, "shelf_life_days": 2,  "lead_time_days": 1, "safety_stock": 1.0},
    "pasta":           {"unit": "kg",  "per_cover": 0.10, "shelf_life_days": 365,"lead_time_days": 2, "safety_stock": 3.0},
    "rice":            {"unit": "kg",  "per_cover": 0.08, "shelf_life_days": 365,"lead_time_days": 2, "safety_stock": 3.0},
    "tomatoes":        {"unit": "kg",  "per_cover": 0.09, "shelf_life_days": 5,  "lead_time_days": 1, "safety_stock": 1.0},
    "lettuce":         {"unit": "heads","per_cover": 0.05,"shelf_life_days": 4,  "lead_time_days": 1, "safety_stock": 2.0},
    "olive_oil":       {"unit": "L",   "per_cover": 0.02, "shelf_life_days": 180,"lead_time_days": 3, "safety_stock": 1.0},
    "eggs":            {"unit": "units","per_cover": 0.50,"shelf_life_days": 14, "lead_time_days": 1, "safety_stock": 12.0},
    "cream":           {"unit": "L",   "per_cover": 0.05, "shelf_life_days": 5,  "lead_time_days": 1, "safety_stock": 1.0},
    "bread_rolls":     {"unit": "units","per_cover": 1.20,"shelf_life_days": 2,  "lead_time_days": 1, "safety_stock": 10.0},
    "wine_house_red":  {"unit": "bottles","per_cover": 0.15,"shelf_life_days": 730,"lead_time_days": 3,"safety_stock": 6.0},
    "wine_house_white":{"unit": "bottles","per_cover": 0.12,"shelf_life_days": 730,"lead_time_days": 3,"safety_stock": 6.0},
}

def load_ingredients() -> dict:
    if os.path.exists(INGREDIENTS_FILE):
        with open(INGREDIENTS_FILE) as f:
            return json.load(f)
    return DEFAULT_INGREDIENTS.copy()

def load_stock() -> dict:
    if os.path.exists(STOCK_FILE):
        with open(STOCK_FILE) as f:
            return json.load(f)
    # default: start with 1 day's worth of stock for ~80 covers
    ingredients = load_ingredients()
    return {name: round(info["per_cover"] * 80 + info["safety_stock"], 2)
            for name, info in ingredients.items()}

def save_stock(stock: dict):
    os.makedirs("data", exist_ok=True)
    with open(STOCK_FILE, "w") as f:
        json.dump(stock, f, indent=2)

def calculate_order(predicted_covers: int, service_date: date) -> dict[str, dict]:

    # returns order quantities per ingredient
    # only orders what is needed beyond current stock, capped by shelf life
    ingredients = load_ingredients()
    stock = load_stock()
    today = date.today()
    order = {}

    for name, info in ingredients.items():
        on_hand = stock.get(name, 0.0)
        needed = predicted_covers * info["per_cover"] + info["safety_stock"]

        # how many days of stock can we hold before it expires?
        usable_days  = min(info["shelf_life_days"], info["lead_time_days"] + 2)
        max_order = needed * usable_days   # do not over-buy perishables

        # net order = what we need minus what we already have, capped
        net = max(0.0, needed - on_hand)
        order_qty = min(net, max_order)
        order_qty = round(order_qty, 2)

        # determine order date so it arrives in time
        order_by = service_date - timedelta(days=info["lead_time_days"])

        order[name] = {
            "order_qty": order_qty,
            "unit": info["unit"],
            "on_hand": round(on_hand, 2),
            "needed": round(needed, 2),
            "order_by": order_by.isoformat(),
            "lead_time": info["lead_time_days"],
            "shelf_life": info["shelf_life_days"],
        }

    return order

def consume_stock(actual_covers: int):
    # deduct actual usage from stock after service. Call after each day
    ingredients = load_ingredients()
    stock       = load_stock()
    for name, info in ingredients.items():
        used = actual_covers * info["per_cover"]
        stock[name] = max(0.0, round(stock.get(name, 0.0) - used, 2))
    save_stock(stock)


def receive_order(order: dict[str, dict]):
    # add ordered quantities to stock (call when delivery arrives)
    stock = load_stock()
    for name, details in order.items():
        stock[name] = round(stock.get(name, 0.0) + details["order_qty"], 2)
    save_stock(stock)


def print_order(order: dict[str, dict]):
    print(f"\n{'Ingredient':<22}{'Order Qty':<12}{'Unit':<10}{'On Hand':<10}{'Needed':<10}{'Order By':<12}{'Lead':<6}{'Shelf'}")
    print("-" * 95)
    for name, d in order.items():
        if d["order_qty"] > 0:
            print(f"{name:<22}{d['order_qty']:<12}{d['unit']:<10}{d['on_hand']:<10}{d['needed']:<10}{d['order_by']:<12}{d['lead_time']:<6}{d['shelf_life']}")
    skipped = [n for n, d in order.items() if d["order_qty"] == 0]
    if skipped:
        print(f"\nNo order needed (sufficient stock): {', '.join(skipped)}")
