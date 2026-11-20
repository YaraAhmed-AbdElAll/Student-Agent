from student_agent.config import FINAL_MIN
from student_agent.tools.course_overview import get_course_overview


def compute_simulation(overview, hypothetical_final):
    """Check what a made-up final score would mean for passing.

    Takes the result of get_course_overview and a score, returns a dictionary.
    """
    status = overview["status"]

    # Cases where a simulation makes no sense
    if status in ("NOT_FOUND", "INVALID_CONFIG"):
        return {"status": status}

    if status == "INSUFFICIENT_DATA":
        return {"status": "MIDTERM_NOT_RECORDED"}

    if status == "FINAL_ALREADY_TAKEN":
        return {
            "status": "FINAL_ALREADY_TAKEN",
            "final_score": overview["final_score"],
            "total": overview["total"],
            "passed": overview["passed"],
        }

    # Check the made-up score itself
    final_max = overview["final_max"]
    is_number = (
        isinstance(hypothetical_final, (int, float))
        and not isinstance(hypothetical_final, bool)
    )
    if not is_number or not (0 <= hypothetical_final <= final_max):
        return {"status": "INVALID_INPUT", "allowed_min": 0, "allowed_max": final_max}

    earned = overview["earned_so_far"]
    pass_mark = overview["pass_mark"]
    pending = overview["pending_assessments_weight"]

    # Worst case: zero on all pending work. Best case: full marks on all of it.
    total_if_pending_zero = round(earned + hypothetical_final, 2)
    total_if_pending_full = round(total_if_pending_zero + pending, 2)

    final_ok = hypothetical_final >= FINAL_MIN
    total_short = total_if_pending_full < pass_mark

    if not final_ok and total_short:
        failed_rule = "BOTH"
    elif not final_ok:
        failed_rule = "FINAL_MINIMUM"
    elif total_short:
        failed_rule = "TOTAL"
    else:
        failed_rule = None

    if failed_rule is not None:
        outcome = "FAIL_GUARANTEED"
    elif total_if_pending_zero >= pass_mark:
        outcome = "PASS_GUARANTEED"
    else:
        outcome = "DEPENDS"

    return {
        "status": "OK",
        "outcome": outcome,
        "hypothetical_final": hypothetical_final,
        "final_min": FINAL_MIN,
        "pass_mark": pass_mark,
        "earned_before_final": earned,
        "pending_assessments_weight": pending,
        "total_if_pending_zero": total_if_pending_zero,
        "total_if_pending_full": total_if_pending_full,
        "failed_rule": failed_rule,
        "margin_over_pass": (
            round(total_if_pending_zero - pass_mark, 2)
            if outcome == "PASS_GUARANTEED" else None
        ),
        "points_short": (
            round(pass_mark - total_if_pending_full, 2) if total_short else None
        ),
        "final_points_short": (
            round(FINAL_MIN - hypothetical_final, 2) if not final_ok else None
        ),
        "needed_from_pending": (
            round(pass_mark - total_if_pending_zero, 2)
            if outcome == "DEPENDS" else None
        ),
    }


def simulate_final_score(user_course_id, hypothetical_final, today=None):
    """What would a made-up final score mean for this student's chance of passing?"""
    overview = get_course_overview(user_course_id, today)
    return compute_simulation(overview, hypothetical_final)