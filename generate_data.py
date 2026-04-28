"""
generate synthetic historical restaurant data for training the forecaster
saves to data/historical.csv
"""

import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# config
START_DATE = date(2023, 1, 1)
END_DATE   = date(2024, 12, 31)

# base covers per hour slot (11am-10pm) for a normal weekday
BASE_HOURLY = {
    11: 8, 12: 22, 13: 28, 14: 18, 15: 10,
    16: 6, 17: 12, 18: 30, 19: 40, 20: 35, 21: 20
}

HOURS = sorted(BASE_HOURLY.keys())

WEATHER_OPTIONS = ["sunny", "cloudy", "rainy", "stormy"]
WEATHER_MULTIPLIER = {"sunny": 1.15, "cloudy": 1.0, "rainy": 0.80, "stormy": 0.55}

EVENT_MULTIPLIER = 1.35   # local event nearby boosts covers
HOLIDAY_MULTIPLIER = 1.50

# public holidays (simplified - just a fixed set)
HOLIDAYS = {
    date(2023, 1, 1), date(2023, 12, 25), date(2023, 12, 26),
    date(2023, 7, 4),  date(2023, 11, 23),
    date(2024, 1, 1),  date(2024, 12, 25), date(2024, 12, 26),
    date(2024, 7, 4),  date(2024, 11, 28),
}

WEEKEND_MULTIPLIER = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.4, 6: 1.3}

def generate_day(d: date) -> list[dict]:
    dow = d.weekday()                          # 0=Mon - 6=Sun
    weather = np.random.choice(WEATHER_OPTIONS, p=[0.4, 0.3, 0.2, 0.1])
    has_event = np.random.random() < 0.10      # 10% chance of local event
    is_holiday = d in HOLIDAYS

    rows = []
    for hour in HOURS:
        base = BASE_HOURLY[hour]
        covers = (
            base
            * WEEKEND_MULTIPLIER[dow]
            * WEATHER_MULTIPLIER[weather]
            * (EVENT_MULTIPLIER  if has_event  else 1.0)
            * (HOLIDAY_MULTIPLIER if is_holiday else 1.0)
        )
        # add realistic noise
        covers = max(0, int(covers + np.random.normal(0, covers * 0.12)))
        rows.append({
            "date":       d.isoformat(),
            "day_of_week": dow,
            "hour":       hour,
            "weather":    weather,
            "has_event":  int(has_event),
            "is_holiday": int(is_holiday),
            "actual_covers": covers,
        })
    return rows

def main():
    os.makedirs("data", exist_ok=True)
    records = []
    current = START_DATE
    while current <= END_DATE:
        records.extend(generate_day(current))
        current += timedelta(days=1)

    df = pd.DataFrame(records)
    df.to_csv("data/historical.csv", index=False)
    print(f"Generated {len(df)} rows -> data/historical.csv")
    print(df.head(11).to_string(index=False))

if __name__ == "__main__":
    main()
