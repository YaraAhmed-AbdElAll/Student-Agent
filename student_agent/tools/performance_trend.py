from student_agent.tools.assessment_breakdown import get_assessment_breakdown
from student_agent.config import (
    TREND_MIN_POINTS,
    TREND_RECENT_COUNT,
    TREND_THRESHOLD,
)


def build_series(items):
    """Keep only graded assessments that have a due date, oldest first."""
    graded = [
        i for i in items
        if i["status"] in ("GRADED", "GRADED_LATE") and i["due_date"] is not None
    ]
    graded.sort(key=lambda i: i["due_date"])
    return [
        {"name": i["name"], "due_date": i["due_date"], "pct": i["pct"]}
        for i in graded
    ]


def average(values):
    return sum(values) / len(values)


def find_biggest_drop(series):
    """Largest fall between two consecutive assessments, or None if it never fell."""
    worst = None
    for before, after in zip(series, series[1:]):
        change = after["pct"] - before["pct"]
        if change < 0 and (worst is None or change < worst["change"]):
            worst = {
                "from": before["name"],
                "to": after["name"],
                "change": round(change, 1),
            }
    return worst


def compute_trend(items):
    series = build_series(items)

    if len(series) < TREND_MIN_POINTS:
        return {"status": "INSUFFICIENT_DATA", "points": len(series), "series": series}

    pcts = [p["pct"] for p in series]
    recent = pcts[-TREND_RECENT_COUNT:]
    earlier = pcts[:-TREND_RECENT_COUNT]

    change = average(recent) - average(earlier)

    if change >= TREND_THRESHOLD:
        direction = "UP"
    elif change <= -TREND_THRESHOLD:
        direction = "DOWN"
    else:
        direction = "FLAT"

    return {
        "status": "OK",
        "direction": direction,
        "earlier_avg_pct": round(average(earlier), 1),
        "recent_avg_pct": round(average(recent), 1),
        "change_pct_points": round(change, 1),
        "biggest_drop": find_biggest_drop(series),
        "series": series,
    }

def get_performance_trend(user_course_id, today=None):
    """Analyse how the student's graded results moved over time."""
    breakdown = get_assessment_breakdown(user_course_id, today)

    if breakdown["status"] == "NOT_FOUND":
        return {"status": "NOT_FOUND"}

    return compute_trend(breakdown["assessments"])