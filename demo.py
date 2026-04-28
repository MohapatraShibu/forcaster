"""
simulates 10 days of predictions + manager corrections to demonstrate
the self-learning feedback loop converging over time.
"""

import json
import os
import random
from datetime import date, timedelta

from cover_forecaster import predict_hourly, apply_correction, save_coefficients, DEFAULT_COEFFICIENTS
from staff_scheduler import build_staffing_plan, peak_staffing
from ingredient_ordering import calculate_order
from feedback_log import log_correction, print_convergence_report

random.seed(7)

# simulated "ground truth" multipliers the restaurant actually experiences
# (slightly different from our starting coefficients — the model must learn these)
TRUE_WEATHER_MULT = {"sunny": 1.20, "cloudy": 0.95, "rainy": 0.70, "stormy": 0.45}
TRUE_DOW_MULT     = {0:1.0, 1:1.0, 2:1.05, 3:1.05, 4:1.15, 5:1.50, 6:1.35}

SCENARIOS = [
    # (date_offset, weather, has_event, is_holiday, reason)
    (0,  "rainy",   False, False, "unexpected rain kept people home"),
    (1,  "sunny",   False, False, ""),
    (2,  "sunny",   True,  False, "street festival nearby"),
    (3,  "cloudy",  False, False, ""),
    (4,  "rainy",   False, False, "rain again"),
    (5,  "sunny",   False, True,  "bank holiday"),
    (6,  "stormy",  False, False, "storm - very quiet"),
    (7,  "sunny",   True,  False, "sports event nearby"),
    (8,  "cloudy",  False, False, ""),
    (9,  "sunny",   False, False, ""),
]

BASE_DAILY_COVERS = 229   # sum of base_hourly values

def simulate_actual(dow, weather, has_event, is_holiday) -> int:
    covers = (BASE_DAILY_COVERS
              * TRUE_DOW_MULT[dow]
              * TRUE_WEATHER_MULT[weather]
              * (1.35 if has_event  else 1.0)
              * (1.50 if is_holiday else 1.0))
    # add +-8% noise
    covers *= random.uniform(0.92, 1.08)
    return max(0, round(covers))

def main():
    # fresh start
    save_coefficients(DEFAULT_COEFFICIENTS.copy())
    for f in os.listdir("data") if os.path.exists("data") else []:
        if f.startswith("pred_") or f == "feedback_log.csv":
            os.remove(os.path.join("data", f))

    print("=" * 65)
    print("DEMO: Self-Learning Forecaster -- 10-day simulation")
    print("=" * 65)

    start = date(2025, 8, 11)   # a monday

    for offset, weather, has_event, is_holiday, reason in SCENARIOS:
        d = start + timedelta(days=offset)
        dow = d.weekday()

        # predict
        hourly    = predict_hourly(dow, weather, has_event, is_holiday)
        predicted = sum(hourly.values())

        # simulate actual
        actual = simulate_actual(dow, weather, has_event, is_holiday)

        error_pct = (actual - predicted) / predicted * 100

        print(f"\n[Day {offset+1}]  {d}  weather={weather:<8}"
              f"  event={has_event}  holiday={is_holiday}")
        print(f"  Predicted: {predicted:>4}  |  Actual: {actual:>4}"
              f"  |  Error: {error_pct:+.1f}%"
              + (f"  <- {reason}" if reason else ""))

        # staff peak
        peak = peak_staffing(build_staffing_plan(hourly))
        print(f"Peak staff: servers={peak['server']} cooks={peak['line_cook']} "
              f"bartenders={peak['bartender']} manager={peak['manager']}")

        # ingredient order (top 3 by qty) ---
        order = calculate_order(predicted, d)
        top3  = sorted(order.items(), key=lambda x: -x[1]["order_qty"])[:3]
        print(f"Top ingredients to order: "
              + ", ".join(f"{n}={v['order_qty']}{v['unit']}" for n, v in top3))

        # apply correction
        apply_correction(dow, weather, has_event, is_holiday,
                         predicted, actual, reason)
        log_correction(d.isoformat(), predicted, actual, reason,
                       dow, weather, has_event, is_holiday)

    print("\n" + "=" * 65)
    print_convergence_report()

if __name__ == "__main__":
    main()
