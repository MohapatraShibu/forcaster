"""
persists every prediction and manager correction to data/feedback_log.csv
used to track how the model converges over time
"""

import csv
import os
from datetime import datetime

LOG_FILE = "data/feedback_log.csv"
FIELDS   = ["timestamp", "service_date", "predicted_total", "actual_total",
            "error_pct", "reason", "dow", "weather", "has_event", "is_holiday"]

def log_correction(service_date: str, predicted: int, actual: int,
                   reason: str, dow: int, weather: str,
                   has_event: bool, is_holiday: bool):
    os.makedirs("data", exist_ok=True)
    write_header = not os.path.exists(LOG_FILE)
    error_pct = round((actual - predicted) / predicted * 100, 1) if predicted else 0

    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp":  datetime.now().isoformat(timespec="seconds"),
            "service_date": service_date,
            "predicted_total": predicted,
            "actual_total": actual,
            "error_pct": error_pct,
            "reason": reason,
            "dow": dow,
            "weather": weather,
            "has_event": int(has_event),
            "is_holiday": int(is_holiday),
        })

def print_convergence_report():
    if not os.path.exists(LOG_FILE):
        print("No feedback logged yet.")
        return

    with open(LOG_FILE) as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No feedback logged yet.")
        return

    errors = [abs(float(r["error_pct"])) for r in rows]
    n = len(errors)
    avg = sum(errors) / n

    # show rolling average over windows of 5 to visualise convergence
    print(f"\nFeedback convergence report  ({n} corrections logged)")
    print(f"{'#':<5}{'Date':<14}{'Predicted':<12}{'Actual':<10}{'Error %':<10}{'Reason'}")
    print("-" * 65)
    for i, r in enumerate(rows, 1):
        print(f"{i:<5}{r['service_date']:<14}{r['predicted_total']:<12}"
              f"{r['actual_total']:<10}{r['error_pct']:<10}{r['reason']}")

    print(f"\nOverall mean absolute error: {avg:.1f}%")

    if n >= 5:
        windows = [errors[max(0, i-4):i+1] for i in range(n)]
        rolling = [sum(w)/len(w) for w in windows]
        print("\nRolling 5-correction MAE (shows convergence trend):")
        for i, val in enumerate(rolling, 1):
            bar = "|" * int(val / 2)
            print(f"  [{i:>3}] {val:5.1f}%  {bar}")
