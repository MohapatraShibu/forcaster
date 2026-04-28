"""
given predicted covers per hour, outputs a staffing plan by role and station.

staffing rules (derived from industry norms):
- 1 server per 15 covers (floor)
- 1 runner per 25 covers
- 1 host per 40 covers (min 1 during open hours)
- kitchen: 1 head chef always, +1 line cook per 20 covers, 1 prep cook per 30 covers
- bar: 1 bartender per 30 covers (min 1 if bar is open: 17:00+)
- manager: 1 always
"""

import math

ROLES = {
    "server":     {"covers_per_staff": 15, "min": 1},
    "runner":     {"covers_per_staff": 25, "min": 1},
    "host":       {"covers_per_staff": 40, "min": 1},
    "line_cook":  {"covers_per_staff": 20, "min": 1},
    "prep_cook":  {"covers_per_staff": 30, "min": 1},
    "bartender":  {"covers_per_staff": 30, "min": 0},  # 0 before 17:00
    "head_chef":  {"covers_per_staff": None, "min": 1},  # always 1
    "manager":    {"covers_per_staff": None, "min": 1},  # always 1
}


def staff_for_covers(covers: int, hour: int) -> dict[str, int]:
    # return required staff count per role for a given covers count and hour
    plan = {}
    for role, cfg in ROLES.items():
        if cfg["covers_per_staff"] is None:
            plan[role] = cfg["min"]
        else:
            needed = math.ceil(covers / cfg["covers_per_staff"])
            # bartender only needed from 17:00 onwards
            if role == "bartender" and hour < 17:
                plan[role] = 0
            else:
                plan[role] = max(cfg["min"], needed)
    return plan

def build_staffing_plan(hourly_covers: dict[int, int]) -> dict[int, dict[str, int]]:
    # return full staffing plan: {hour: {role: count}}
    return {hour: staff_for_covers(covers, hour)
            for hour, covers in hourly_covers.items()}

def peak_staffing(staffing_plan: dict[int, dict[str, int]]) -> dict[str, int]:
    # return the maximum staff needed per role across all hours (for scheduling)
    peak = {}
    for hour_plan in staffing_plan.values():
        for role, count in hour_plan.items():
            peak[role] = max(peak.get(role, 0), count)
    return peak

def print_staffing_plan(staffing_plan: dict[int, dict[str, int]]):
    print(f"\n{'Hour':<6}", end="")
    roles = list(ROLES.keys())
    for r in roles:
        print(f"{r:<12}", end="")
    print()
    print("-" * (6 + 12 * len(roles)))
    for hour in sorted(staffing_plan):
        print(f"{hour:<6}", end="")
        for r in roles:
            print(f"{staffing_plan[hour].get(r, 0):<12}", end="")
        print()

    peak = peak_staffing(staffing_plan)
    print("\nPeak staff needed (schedule at least this many per role):")
    for role, count in peak.items():
        print(f"  {role:<14}: {count}")
