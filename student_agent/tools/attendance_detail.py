from datetime import date

from student_agent.config import ATTENDANCE_RECENT_COUNT
from student_agent.db import get_connection

def select_counted_lectures(rows, enrollment_date, today):
    """Keep the lectures that count: already held, and held after the student joined.

    Each row is (name, lecture_date, topic, attended).
    attended is True, False, or None when nothing was recorded.
    """
    counted = []

    for name, lecture_date, topic, attended in rows:
        if lecture_date > today:
            continue  # not held yet
        if enrollment_date is not None and lecture_date < enrollment_date:
            continue  # held before the student joined

        counted.append({
            "name": name,
            "date": lecture_date.isoformat(),
            "topic": topic,
            "attended": attended,
        })

    counted.sort(key=lambda lec: lec["date"])
    return counted


def count_attendance(counted):
    """Count attended, absent and unrecorded lectures."""
    recorded = [lec for lec in counted if lec["attended"] is not None]
    attended = sum(1 for lec in recorded if lec["attended"])
    absent = len(recorded) - attended

    pct = round(attended / len(recorded) * 100, 1) if recorded else None

    return {
        "held": len(counted),
        "recorded": len(recorded),
        "not_recorded": len(counted) - len(recorded),
        "attended": attended,
        "absent": absent,
        "attendance_pct": pct,
    }


def list_absences(counted):
    """The lectures the student was recorded absent from."""
    return [
        {"name": lec["name"], "date": lec["date"], "topic": lec["topic"]}
        for lec in counted
        if lec["attended"] is False
    ]

def absence_streaks(counted):
    """Longest run of consecutive recorded absences, and the run happening now.

    A lecture with no recorded attendance breaks a run: we only claim
    'consecutive' when we have evidence for every lecture in the run.
    """
    longest_run = []
    run = []

    for lec in counted:
        if lec["attended"] is False:
            run.append(lec)
            if len(run) > len(longest_run):
                longest_run = list(run)
        else:
            run = []

    return {
        "longest_absence_streak": len(longest_run),
        "longest_streak_from": longest_run[0]["name"] if longest_run else None,
        "longest_streak_to": longest_run[-1]["name"] if longest_run else None,
        "current_absence_streak": len(run),
    }


def recent_attendance(counted):
    """Attendance in the last few lectures that have a recorded result."""
    recorded = [lec for lec in counted if lec["attended"] is not None]
    recent = recorded[-ATTENDANCE_RECENT_COUNT:]

    if not recent:
        return {"lectures": 0, "attendance_pct": None}

    attended = sum(1 for lec in recent if lec["attended"])
    return {
        "lectures": len(recent),
        "attendance_pct": round(attended / len(recent) * 100, 1),
    }


def build_attendance(rows, enrollment_date, today):
    """Put everything together for one student in one course."""
    counted = select_counted_lectures(rows, enrollment_date, today)

    if not counted:
        return {"status": "NO_LECTURES_HELD"}

    counts = count_attendance(counted)
    status = "OK" if counts["recorded"] > 0 else "NO_ATTENDANCE_RECORDED"

    return {
        "status": status,
        **counts,
        "absences": list_absences(counted),
        **absence_streaks(counted),
        "recent": recent_attendance(counted),
    }


ENROLLMENT_QUERY = """
    SELECT enrollment_date FROM user_courses WHERE user_course_id = %s
"""

LECTURES_QUERY = """
    SELECT l.name, l.lecture_date, l.topic, la.attended
    FROM user_courses uc
    JOIN lectures l ON l.course_id = uc.course_id
    LEFT JOIN lecture_attendance la
           ON la.lecture_id = l.lecture_id
          AND la.user_course_id = uc.user_course_id
    WHERE uc.user_course_id = %s
    ORDER BY l.lecture_date, l.lecture_id
"""


def get_attendance_detail(user_course_id, today=None):
    """Fetch this student's lectures and attendance, then analyse them."""
    today = today or date.today()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(ENROLLMENT_QUERY, (user_course_id,))
            enrollment_row = cur.fetchone()
            if enrollment_row is None:
                return {"status": "NOT_FOUND"}

            cur.execute(LECTURES_QUERY, (user_course_id,))
            rows = cur.fetchall()
    finally:
        conn.close()

    (enrollment_date,) = enrollment_row
    return build_attendance(rows, enrollment_date, today)