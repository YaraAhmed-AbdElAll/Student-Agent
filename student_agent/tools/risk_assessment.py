from student_agent.config import (
    ATTENDANCE_BAR_PCT,
    RISK_ABSENCE_STREAK,
    RISK_ATTENDANCE_HIGH,
    RISK_ATTENDANCE_MEDIUM,
    RISK_FINAL_PCT_HIGH,
    RISK_FINAL_PCT_MEDIUM,
    RISK_MISSING_POINTS_HIGH,
    RISK_MISSING_POINTS_MEDIUM,
    RISK_URGENT_DAYS,
)
from student_agent.tools.attendance_detail import get_attendance_detail
from student_agent.tools.course_overview import (
    compute_course_overview,
    get_course_overview,
)
from student_agent.tools.missing_work import get_missing_work
from student_agent.tools.performance_trend import get_performance_trend

LEVEL_ORDER = ["LOW", "MEDIUM", "HIGH"]


def make_evidence(code, level, **facts):
    """One piece of evidence: a code, a level, and the numbers behind it."""
    return {"code": code, "level": level, "facts": facts}


def overview_evidence(overview):
    if overview["status"] != "OK":
        return []

    if not overview["pass_still_possible"]:
        return [make_evidence(
            "PASS_IMPOSSIBLE", "HIGH",
            required_in_final=overview["required_in_final"],
            final_max=overview["final_max"],
        )]

    pct = overview["required_pct_of_final"]
    if pct >= RISK_FINAL_PCT_HIGH:
        level = "HIGH"
    elif pct >= RISK_FINAL_PCT_MEDIUM:
        level = "MEDIUM"
    else:
        return []

    return [make_evidence(
        "HIGH_FINAL_REQUIREMENT", level,
        required_in_final=overview["required_in_final"],
        required_pct_of_final=pct,
        binding_rule=overview["binding_rule"],
    )]


def trend_evidence(trend):
    if trend["status"] == "OK" and trend["direction"] == "DOWN":
        return [make_evidence(
            "TREND_DOWN", "MEDIUM",
            earlier_avg_pct=trend["earlier_avg_pct"],
            recent_avg_pct=trend["recent_avg_pct"],
            change_pct_points=trend["change_pct_points"],
            biggest_drop=trend["biggest_drop"],
        )]
    return []


def attendance_evidence(attendance):
    if attendance["status"] != "OK":
        return []

    found = []
    pct = attendance["attendance_pct"]

    if pct < RISK_ATTENDANCE_HIGH:
        level = "HIGH"
    elif pct < RISK_ATTENDANCE_MEDIUM:
        level = "MEDIUM"
    else:
        level = None
    if level is not None:
        found.append(make_evidence(
            "LOW_ATTENDANCE", level,
            attendance_pct=pct,
            absent=attendance["absent"],
            recorded=attendance["recorded"],
        ))

    if ATTENDANCE_BAR_PCT is not None and pct < ATTENDANCE_BAR_PCT:
        found.append(make_evidence(
            "EXAM_BAR_RISK", "HIGH",
            attendance_pct=pct, bar_pct=ATTENDANCE_BAR_PCT,
        ))

    streak = attendance["current_absence_streak"]
    if streak >= RISK_ABSENCE_STREAK:
        found.append(make_evidence(
            "ABSENCE_STREAK", "MEDIUM", current_absence_streak=streak,
        ))

    return found


def missing_evidence(missing):
    if missing["status"] != "OK":
        return []

    lost = missing["missing_points_lost"]
    if lost >= RISK_MISSING_POINTS_HIGH:
        level = "HIGH"
    elif lost >= RISK_MISSING_POINTS_MEDIUM:
        level = "MEDIUM"
    else:
        return []

    return [make_evidence(
        "MISSING_WORK", level,
        missing_count=missing["missing_count"],
        missing_points_lost=lost,
        names=[m["name"] for m in missing["missing"]],
    )]


def find_data_gaps(overview, trend, attendance):
    """What we could not see. The agent should tell the student about these."""
    gaps = []

    if overview["status"] == "INSUFFICIENT_DATA":
        gaps.append("MIDTERM_NOT_RECORDED")

    if overview.get("course_total_ok") is False:
       gaps.append("COURSE_TOTAL_MISMATCH")    

    days = overview["days_to_final"]
    if overview["status"] == "OK" and days is not None and days < 0:
        gaps.append("FINAL_RESULT_NOT_RECORDED")

    if trend["status"] == "INSUFFICIENT_DATA":
        gaps.append("NOT_ENOUGH_GRADES_FOR_TREND")

    if attendance["status"] in ("NO_LECTURES_HELD", "NO_ATTENDANCE_RECORDED"):
        gaps.append("NO_ATTENDANCE_DATA")

    return gaps


def pick_level(evidence, days):
    """Highest level among the evidence, raised one step if the exam is close."""
    if not evidence:
        return "LOW", False

    level = max((e["level"] for e in evidence), key=LEVEL_ORDER.index)
    if level == "MEDIUM" and days is not None and 0 <= days < RISK_URGENT_DAYS:
        return "HIGH", True
    return level, False


def midterm_scenarios(overview, other_evidence):
    """The student's risk if the missing midterm were 0, and if it were full marks."""
    days = overview["days_to_final"]
    scenarios = {}

    for name, midterm in (
        ("if_midterm_zero", 0.0),
        ("if_midterm_full", overview["midterm_max"]),
    ):
        scenario = compute_course_overview(
            pass_mark=overview["pass_mark"],
            final_max=overview["final_max"],
            midterm=midterm,
            assessments_earned=overview["assessments_earned"],
            pending_weight=overview["pending_assessments_weight"],
            final_score=None,
            days_to_final=days,
            midterm_max=overview["midterm_max"],
        )
        level, escalated = pick_level(
            overview_evidence(scenario) + other_evidence, days
        )
        scenarios[name] = {
            "risk_level": level,
            "escalated_by_time": escalated,
            "required_in_final": scenario["required_in_final"],
            "required_pct_of_final": scenario["required_pct_of_final"],
            "pass_still_possible": scenario["pass_still_possible"],
        }

    return scenarios


def compute_risk(overview, trend, attendance, missing):
    """Combine the results of four tools into one risk level with evidence."""
    results = (overview, trend, attendance, missing)

    if any(r["status"] == "NOT_FOUND" for r in results):
        return {"status": "NOT_FOUND"}
    if overview["status"] == "INVALID_CONFIG":
        return {"status": "INVALID_CONFIG"}
    if overview["status"] == "FINAL_ALREADY_TAKEN":
        return {
            "status": "FINAL_ALREADY_TAKEN",
            "total": overview["total"],
            "passed": overview["passed"],
        }

    days = overview["days_to_final"]
    gaps = find_data_gaps(overview, trend, attendance)
    other = (
        trend_evidence(trend)
        + attendance_evidence(attendance)
        + missing_evidence(missing)
    )

    scenarios = None
    risk_range = None
    can_simulate_midterm = (
        overview["status"] == "INSUFFICIENT_DATA"
        and overview["midterm_max"] is not None
    )

    if can_simulate_midterm:
        # Midterm not recorded: work out both extremes instead of guessing.
        scenarios = midterm_scenarios(overview, other)
        worst = scenarios["if_midterm_zero"]
        best = scenarios["if_midterm_full"]
        evidence = other
        escalated = worst["escalated_by_time"] and best["escalated_by_time"]

        if worst["risk_level"] == best["risk_level"]:
            level = worst["risk_level"]
        else:
            level = "RANGE"
            risk_range = {
                "best_case": best["risk_level"],
                "worst_case": worst["risk_level"],
            }
    else:
        evidence = overview_evidence(overview) + other
        level, escalated = pick_level(evidence, days)
        if not evidence and "MIDTERM_NOT_RECORDED" in gaps:
            level = "UNKNOWN"

    evidence.sort(key=lambda e: LEVEL_ORDER.index(e["level"]), reverse=True)

    return {
        "status": "OK",
        "risk_level": level,
        "risk_range": risk_range,
        "escalated_by_time": escalated,
        "days_to_final": days,
        "evidence": evidence,
        "midterm_scenarios": scenarios,
        "data_gaps": gaps,
    }


def get_risk_assessment(user_course_id, today=None):
    """Run the four analysis tools and combine them into a risk assessment."""
    return compute_risk(
        get_course_overview(user_course_id, today),
        get_performance_trend(user_course_id, today),
        get_attendance_detail(user_course_id, today),
        get_missing_work(user_course_id, today),
    )