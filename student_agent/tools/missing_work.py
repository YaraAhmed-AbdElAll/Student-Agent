from datetime import date

from student_agent.tools.assessment_breakdown import get_assessment_breakdown


def find_missing_work(items, today):
    """Split the classified assessments into missing, late and upcoming work."""
    missing = []
    late = []
    upcoming = []

    for item in items:
        status = item["status"]
        due = date.fromisoformat(item["due_date"]) if item["due_date"] is not None else None

        if status == "MISSING":
            missing.append({
                "name": item["name"],
                "type": item["type"],
                "weight": item["weight"],
                "due_date": item["due_date"],
                "days_overdue": (today - due).days,
                "points_lost": item["points_lost"],
            })
        elif status == "GRADED_LATE":
            late.append({
                "name": item["name"],
                "type": item["type"],
                "due_date": item["due_date"],
                "pct": item["pct"],
            })
        elif status == "PENDING":
            upcoming.append({
                "name": item["name"],
                "type": item["type"],
                "weight": item["weight"],
                "due_date": item["due_date"],
                "days_left": (due - today).days if due is not None else None,
            })

    missing.sort(key=lambda m: m["points_lost"], reverse=True)
    late.sort(key=lambda w: w["due_date"])
    upcoming.sort(key=lambda u: (u["days_left"] is None, u["days_left"] or 0))

    return {
        "status": "OK",
        "missing_count": len(missing),
        "missing_points_lost": round(sum(m["points_lost"] for m in missing), 2),
        "missing": missing,
        "late_count": len(late),
        "late": late,
        "upcoming": upcoming,
    }


def get_missing_work(user_course_id, today=None):
    """List the student's missing, late and upcoming assessments."""
    today = today or date.today()
    breakdown = get_assessment_breakdown(user_course_id, today)

    if breakdown["status"] != "OK":
        return {"status": breakdown["status"]}

    return find_missing_work(breakdown["assessments"], today)