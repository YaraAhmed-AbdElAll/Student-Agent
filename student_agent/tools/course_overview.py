from student_agent.config import COURSE_TOTAL, FINAL_MIN
from datetime import date

from student_agent.config import FINAL_MIN
from student_agent.db import get_connection


def compute_course_overview(pass_mark, final_max, midterm, assessments_earned,
                            pending_weight, final_score, days_to_final,midterm_max=None,coursework_max=None):
    """Calculate the student's official position in one course.

    Takes plain numbers (no database) and returns a dictionary.
    """

    course_total = (
        round(coursework_max + final_max, 2) if coursework_max is not None else None
    )
    base = {
        "pass_mark": pass_mark,
        "assessments_earned": round(assessments_earned, 2),
        "midterm": midterm,
        "pending_assessments_weight": round(pending_weight, 2),
        "final_min": FINAL_MIN,
        "final_max": final_max,
        "days_to_final": days_to_final,
        "midterm_max": midterm_max,
        "coursework_max": coursework_max,
        "course_total": course_total,
        "course_total_ok": None if course_total is None else course_total == COURSE_TOTAL,
    }

    if FINAL_MIN > final_max:
        return {**base, "status": "INVALID_CONFIG"}

    if midterm is None:
        return {**base, "status": "INSUFFICIENT_DATA"}

    earned = assessments_earned + midterm

    # Case 1: the final exam is already taken
    if final_score is not None:
        total = earned + final_score
        passed = total >= pass_mark and final_score >= FINAL_MIN
        return {
            **base,
            "status": "FINAL_ALREADY_TAKEN",
            "earned_before_final": round(earned, 2),
            "final_score": final_score,
            "total": round(total, 2),
            "passed": passed,
        }

    # Case 2: the final exam is still ahead
    needed_for_total = round(pass_mark - earned, 2)
    required = max(needed_for_total, FINAL_MIN)

    if needed_for_total > FINAL_MIN:
        binding_rule = "TOTAL"
    elif needed_for_total < FINAL_MIN:
        binding_rule = "FINAL_MINIMUM"
    else:
        binding_rule = "BOTH"

    return {
        **base,
        "status": "OK",
        "earned_so_far": round(earned, 2),
        "required_in_final": round(required, 2),
        "required_pct_of_final": round(required / final_max * 100, 1),
        "binding_rule": binding_rule,
        "pass_still_possible": required <= final_max,
    }


def sum_assessments(rows, today):
    """Add up quizzes, assignments, etc. for one student in one course.

    Each row is (weight, max_score, due_date, score).
    Returns (earned, pending_weight).
    """
    earned = 0.0
    pending = 0.0

    for weight, max_score, due_date, score in rows:
        if score is not None:
            earned += float(score) / float(max_score) * float(weight)
        elif due_date is None or due_date > today:
            pending += float(weight)
        # else: the due date passed and nothing was submitted -> counts as zero

    return round(earned, 2), round(pending, 2)


COURSE_QUERY = """
    SELECT c.pass_mark, c.final_max, c.final_exam_date, g.midterm, g.final,
           c.midterm_max,
           (SELECT COALESCE(SUM(a.weight), 0)
            FROM assessments a WHERE a.course_id = c.course_id)
    FROM user_courses uc
    JOIN courses c ON c.course_id = uc.course_id
    LEFT JOIN course_grades g ON g.user_course_id = uc.user_course_id
    WHERE uc.user_course_id = %s
"""

ASSESSMENTS_QUERY = """
    SELECT a.weight, a.max_score, a.due_date, s.score
    FROM user_courses uc
    JOIN assessments a ON a.course_id = uc.course_id
    LEFT JOIN assessment_submissions s
           ON s.assessment_id = a.assessment_id
          AND s.user_course_id = uc.user_course_id
    WHERE uc.user_course_id = %s
"""


def _to_float(value):
    return float(value) if value is not None else None


def get_course_overview(user_course_id, today=None):
    """Fetch the numbers from the database, then run the calculation."""
    today = today or date.today()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(COURSE_QUERY, (user_course_id,))
            course_row = cur.fetchone()
            if course_row is None:
                return {"status": "NOT_FOUND"}

            cur.execute(ASSESSMENTS_QUERY, (user_course_id,))
            assessment_rows = cur.fetchall()
    finally:
        conn.close()

        (pass_mark, final_max, exam_date, midterm, final_score,
     midterm_max, assessments_weight) = course_row
    midterm_max = _to_float(midterm_max)
    coursework_max = (
        float(assessments_weight) + midterm_max if midterm_max is not None else None
    )
    earned, pending = sum_assessments(assessment_rows, today)
    days = (exam_date - today).days if exam_date is not None else None

    return compute_course_overview(
        pass_mark=float(pass_mark),
        final_max=float(final_max),
        midterm=_to_float(midterm),
        assessments_earned=earned,
        pending_weight=pending,
        final_score=_to_float(final_score),
        days_to_final=days,
        midterm_max=midterm_max,
        coursework_max=coursework_max,
    )