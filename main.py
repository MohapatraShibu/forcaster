"""
CLI for the Restaurant Resource Planning System

Commands:
predict -- forecast covers, staff, and ingredients for a given date
correct -- submit actual covers after service (triggers learning)
report -- show convergence history
reset  -- reset coefficients to defaults (for demo/testing)

usage examples:
  python main.py predict --date 2025-08-15 --weather rainy --event
  python main.py correct --date 2025-08-15 --weather rainy --actual 85 --reason "heavy rain all evening"
  python main.py report
  python main.py reset
"""

import argparse
import json
import os
from datetime import date, datetime

from cover_forecaster import (predict_hourly, apply_correction,
                                  load_coefficients, save_coefficients,
                                  DEFAULT_COEFFICIENTS)
from staff_scheduler import build_staffing_plan, print_staffing_plan
from ingredient_ordering import calculate_order, print_order
from feedback_log import log_correction, print_convergence_report

DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def cmd_predict(args):
    target = datetime.strptime(args.date, "%Y-%m-%d").date()
    dow    = target.weekday()

    print(f"\n{'='*60}")
    print(f"  FORECAST  --  {target}  ({DAY_NAMES[dow]})")
    print(f"  Weather: {args.weather}  |  Event: {args.event}  |  Holiday: {args.holiday}")
    print(f"{'='*60}")

    # 1. cover prediction
    hourly = predict_hourly(dow, args.weather, args.event, args.holiday)
    total  = sum(hourly.values())

    print(f"\nHourly cover forecast (total: {total}):")
    print(f"  {'Hour':<8}", end="")
    for h in sorted(hourly):
        print(f"{h:<6}", end="")
    print()
    print(f"  {'Covers':<8}", end="")
    for h in sorted(hourly):
        print(f"{hourly[h]:<6}", end="")
    print()

    # 2. staffing plan
    print("\nStaffing plan:")
    staffing = build_staffing_plan(hourly)
    print_staffing_plan(staffing)

    # 3. ingredient order
    print("\nIngredient order:")
    order = calculate_order(total, target)
    print_order(order)

    # save prediction so 'correct' can reference it
    os.makedirs("data", exist_ok=True)
    pred_file = f"data/pred_{args.date}.json"
    with open(pred_file, "w") as f:
        json.dump({"predicted_total": total, "dow": dow,
                   "weather": args.weather, "event": int(args.event),
                   "holiday": int(args.holiday)}, f)
    print(f"\nPrediction saved -> {pred_file}")

def cmd_correct(args):
    pred_file = f"data/pred_{args.date}.json"
    if not os.path.exists(pred_file):
        print(f"No saved prediction found for {args.date}. Run 'predict' first.")
        return

    with open(pred_file) as f:
        pred = json.load(f)

    predicted = pred["predicted_total"]
    actual = args.actual
    dow = pred["dow"]
    weather = pred["weather"]
    has_event = bool(pred["event"])
    is_holiday= bool(pred["holiday"])

    apply_correction(dow, weather, has_event, is_holiday,
                     predicted, actual, args.reason)

    log_correction(args.date, predicted, actual, args.reason,
                   dow, weather, has_event, is_holiday)

def cmd_report(_args):
    print_convergence_report()

def cmd_reset(_args):
    save_coefficients(DEFAULT_COEFFICIENTS.copy())
    print("Coefficients reset to defaults.")

def main():
    parser = argparse.ArgumentParser(
        description="Restaurant Resource Planning — Self-Learning Forecaster")
    sub = parser.add_subparsers(dest="command", required=True)

    # predict
    p = sub.add_parser("predict", help="Forecast covers, staff, and ingredients")
    p.add_argument("--date", required=True, help="Service date YYYY-MM-DD")
    p.add_argument("--weather", required=True,
                   choices=["sunny","cloudy","rainy","stormy"])
    p.add_argument("--event", action="store_true", help="Local event nearby?")
    p.add_argument("--holiday", action="store_true", help="Public holiday?")

    # correct
    c = sub.add_parser("correct", help="Submit actual covers after service")
    c.add_argument("--date", required=True, help="Service date YYYY-MM-DD")
    c.add_argument("--actual", required=True, type=int, help="Actual covers served")
    c.add_argument("--reason", default="", help="Optional reason for deviation")

    # report
    sub.add_parser("report", help="Show convergence history")

    # reset
    sub.add_parser("reset", help="Reset coefficients to defaults")

    args = parser.parse_args()
    {"predict": cmd_predict, "correct": cmd_correct,
     "report":  cmd_report, "reset":   cmd_reset}[args.command](args)

if __name__ == "__main__":
    main()
