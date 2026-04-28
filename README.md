# Restaurant Resource Planning System - Self-Learning Forecaster

A system that predicts **covers (customers)**, **staff requirements**, and
**ingredient orders** for any upcoming service day, and self-corrects its
predictions over time using manager feedback.

---

## Project Structure

```
forecaster/
├── venv/                    
├── data/
│   ├── historical.csv       # 2 years of synthetic training data (generated)
│   ├── coefficients.json    # Learnable model coefficients (auto-updated)
│   ├── stock.json           # Current ingredient stock levels
│   ├── feedback_log.csv     # Every prediction + correction (convergence log)
│   └── pred_YYYY-MM-DD.json # Saved prediction per day (for correction lookup)
├── generate_data.py         # Generates synthetic historical dataset
├── cover_forecaster.py      # Cover prediction model + feedback/learning logic
├── staff_scheduler.py       # Maps predicted covers -> staff by role & station
├── ingredient_ordering.py   # Calculates ingredient orders (shelf life + lead time)
├── feedback_log.py          # Logs corrections, prints convergence report
├── main.py                  # CLI entry point
├── demo.py                  # 10-day simulation showing the feedback loop
└── requirements.txt
```

---

## Setup

```bash
# 1. Create and activate the venv (already done - lives inside this folder)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate the dataset
python generate_data.py
```

---

## How to Use

### Predict a day
```bash
python main.py predict --date 2025-09-12 --weather sunny
python main.py predict --date 2025-09-13 --weather rainy --event
python main.py predict --date 2025-12-25 --weather cloudy --holiday
```

### Submit actual covers after service (triggers learning)
```bash
python main.py correct --date 2025-09-12 --actual 245 --reason quiet_monday
python main.py correct --date 2025-09-13 --actual 310 --reason festival_ran_late
```

### View convergence history
```bash
python main.py report
```

### Reset coefficients to defaults
```bash
python main.py reset
```

### Run the 10-day demo simulation
```bash
python demo.py
```

---

## How the Model Works

### 1. Cover Prediction (`cover_forecaster.py`)

The model is a **multiplicative linear model** with learnable coefficients:

```
predicted_covers(hour) = base_hourly[hour]
                         * dow_coeff[day_of_week]
                         * weather_coeff[weather]
                         * event_coeff    (if local event)
                         * holiday_coeff  (if public holiday)
```

All coefficients start at sensible defaults and are stored in
`data/coefficients.json`. They update automatically after every correction.

### 2. Staff Scheduling (`staff_scheduler.py`)

Staffing rules per hour based on predicted covers:

| Role        | Covers per staff | Min |
|-------------|-----------------|-----|
| Server      | 15              | 1   |
| Runner      | 25              | 1   |
| Host        | 40              | 1   |
| Line cook   | 20              | 1   |
| Prep cook   | 30              | 1   |
| Bartender   | 30              | 0 (before 17:00), 1 after |
| Head chef   | -               | 1 always |
| Manager     | -               | 1 always |

Output: per-hour staffing table + peak headcount per role for scheduling.

### 3. Ingredient Ordering (`ingredient_ordering.py`)

For each ingredient:
```
order_qty = max(0, needed - on_hand)
needed    = predicted_covers * per_cover_usage + safety_stock
```

Perishables are capped so you never order more than `shelf_life_days` worth.
Each ingredient has a `lead_time_days` so the system tells you the latest
date to place the order.

---

## The Feedback Loop (Self-Learning)

This is the core of the system. After each service day, the manager runs:

```bash
python main.py correct --date YYYY-MM-DD --actual <covers> --reason <why>
```

The system computes:
```
ratio = actual / predicted
```

Then nudges each **active coefficient** (the ones that applied that day) toward
the true value using gradient descent with a learning rate of 0.10:

```
new_coeff = old_coeff + lr * (ratio * old_coeff - old_coeff)
          = old_coeff * (1 + lr * (ratio - 1))
```

- If `ratio > 1` (we under-predicted): coefficients increase
- If `ratio < 1` (we over-predicted): coefficients decrease
- Only the coefficients that were **active** that day are updated
  (e.g. `weather[rainy]` only updates on rainy days)

Over many corrections, each coefficient converges toward the true multiplier
for that condition. The `report` command shows the rolling mean absolute error
trend so you can see convergence happening.

---

## Dataset

`data/historical.csv` - 8,041 rows covering 2023-01-01 to 2024-12-31.

Each row is one hour of one day:

| Column         | Description                          |
|----------------|--------------------------------------|
| date           | Service date                         |
| day_of_week    | 0=Monday … 6=Sunday                  |
| hour           | Hour of service (11–21)              |
| weather        | sunny / cloudy / rainy / stormy      |
| has_event      | 1 if local event nearby              |
| is_holiday     | 1 if public holiday                  |
| actual_covers  | Simulated actual covers that hour    |

Generated with realistic multipliers + ±12% Gaussian noise.

---

## Dependencies (all free / open-source)

- `numpy` - numerical operations
- `pandas` - data generation and CSV handling
- `scikit-learn` - available for future model extensions
