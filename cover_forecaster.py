"""
predicts hourly covers using a linear model with learnable coefficients
coefficients are stored in data/coefficients.json and updated via manager feedback
model:
  predicted_covers(hour) = base_hourly[hour]
                           * dow_coeff[day_of_week]
                           * weather_coeff[weather]
                           * event_coeff  (if has_event)
                           * holiday_coeff (if is_holiday)
feedback loop:
After a day passes, manager submits actual total covers
We compute the ratio (actual / predicted) and nudge each active
coefficient toward that ratio using a small learning rate
"""

import json
import os
from datetime import date

COEFF_FILE = "data/coefficients.json"

# default coefficients (start neutral, will self-correct over time)
DEFAULT_COEFFICIENTS = {
    "base_hourly": {
        "11": 8.0, "12": 22.0, "13": 28.0, "14": 18.0, "15": 10.0,
        "16": 6.0, "17": 12.0, "18": 30.0, "19": 40.0, "20": 35.0, "21": 20.0
    },
    "dow": {          # 0=Mon … 6=Sun
        "0": 1.00, "1": 1.00, "2": 1.00, "3": 1.00,
        "4": 1.10, "5": 1.40, "6": 1.30
    },
    "weather": {
        "sunny": 1.15, "cloudy": 1.00, "rainy": 0.80, "stormy": 0.55
    },
    "event":   1.35,
    "holiday": 1.50,
    "learning_rate": 0.10,   # how aggressively to update on each correction
}

HOURS = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]

def load_coefficients() -> dict:
    if os.path.exists(COEFF_FILE):
        with open(COEFF_FILE) as f:
            return json.load(f)
    return DEFAULT_COEFFICIENTS.copy()

def save_coefficients(coeffs: dict):
    os.makedirs("data", exist_ok=True)
    with open(COEFF_FILE, "w") as f:
        json.dump(coeffs, f, indent=2)

def predict_hourly(day_of_week: int, weather: str,
                   has_event: bool, is_holiday: bool) -> dict[int, int]:
    # return predicted covers for each hour as {hour: covers}.
    c = load_coefficients()
    result = {}
    for hour in HOURS:
        base  = c["base_hourly"][str(hour)]
        cover = (
            base
            * c["dow"][str(day_of_week)]
            * c["weather"].get(weather, 1.0)
            * (c["event"]   if has_event  else 1.0)
            * (c["holiday"] if is_holiday else 1.0)
        )
        result[hour] = max(0, round(cover))
    return result

def apply_correction(day_of_week: int, weather: str,
                     has_event: bool, is_holiday: bool,
                     predicted_total: int, actual_total: int,
                     reason: str = ""):
    # nudge coefficients based on the ratio actual/predicted
    # only the coefficients that were 'active' for this day are updated
    
    if predicted_total == 0:
        print("Cannot correct — predicted total is 0.")
        return

    c  = load_coefficients()
    lr = c["learning_rate"]
    ratio = actual_total / predicted_total   # >1 means we under-predicted

    # update day-of-week coefficient
    old = c["dow"][str(day_of_week)]
    c["dow"][str(day_of_week)] = round(old + lr * (ratio * old - old), 4)

    # update weather coefficient
    old = c["weather"][weather]
    c["weather"][weather] = round(old + lr * (ratio * old - old), 4)

    # update event coefficient only if event was active
    if has_event:
        old = c["event"]
        c["event"] = round(old + lr * (ratio * old - old), 4)

    # update holiday coefficient only if holiday was active
    if is_holiday:
        old = c["holiday"]
        c["holiday"] = round(old + lr * (ratio * old - old), 4)

    save_coefficients(c)

    delta = actual_total - predicted_total
    sign  = "+" if delta >= 0 else ""
    print(f"\nCorrection applied (reason: '{reason or 'none'}')")
    print(f"Predicted: {predicted_total} | Actual: {actual_total}  |  Delta: {sign}{delta}")
    print(f"Ratio: {ratio:.3f} -> coefficients nudged by lr={lr}")
    _print_changed_coeffs(c, day_of_week, weather, has_event, is_holiday)

def _print_changed_coeffs(c, dow, weather, has_event, is_holiday):
    print(f"Updated coefficients:")
    print(f"dow[{dow}] = {c['dow'][str(dow)]}")
    print(f"weather[{weather}] = {c['weather'][weather]}")
    if has_event:
        print(f"event = {c['event']}")
    if is_holiday:
        print(f"holiday = {c['holiday']}")
