from datetime import date

from student_agent.db import get_connection


def classify_assessment(name, kind, weight, max_score, due_date, score,
                        submitted_at, today):
    """Classify an assessment as graded,GRADED_LATE, pending, or missing."""
    weight = float(weight)
    max_score = float(max_score)


    item = {
    "name": name,
    "type": kind,
    "weight": weight,
    "max_score": max_score,
    "due_date": due_date.isoformat() if due_date is not None else None,
    "score": None,
    "pct": None,
    "points_earned": None,
    "points_lost": None,
    }

    if score is not None:
     score = float(score)
     earned = round(score / max_score * weight, 2)

     was_late = (
      submitted_at is not None
      and due_date is not None
      and submitted_at.date() > due_date
      ) 

     item.update({
    "status": "GRADED_LATE" if was_late else "GRADED",
    "score": score, # Score for the assessment
    "pct": round(score / max_score * 100, 1),# Percentage score for the assessment
    "points_earned": earned, # Points earned for the assessment
    "points_lost": round(weight - earned, 2), # Points lost for the assessment
     })

    elif due_date is None or due_date > today:
     item["status"] = "PENDING" 

    else:
     item.update({
        "status": "MISSING",
        "points_earned": 0.0,
        "points_lost": weight,
    }) 

    return item  

def list_assessments(rows, today):
    """Classify every assessment row.

    Each row is (name, kind, weight, max_score, due_date, score, submitted_at).
    """
    items = []
    for name, kind, weight, max_score, due_date, score, submitted_at in rows:
        items.append(classify_assessment(
            name, kind, weight, max_score, due_date, score, submitted_at, today
        ))
    return items


def summarize_by_type(items):
    """Group the classified assessments by type (quiz, assignment, ...)."""
    groups = {}

    for item in items:
        kind = item["type"]

        if kind not in groups:
            groups[kind] = {
                "count": 0, "graded": 0, "late": 0, "missing": 0, "pending": 0,
                "points_earned": 0.0, "points_lost": 0.0,
            }

        g = groups[kind]
        g["count"] += 1

        if item["status"] == "PENDING":
            g["pending"] += 1
            continue

        if item["status"] == "MISSING":
            g["missing"] += 1
        else:
            g["graded"] += 1
            if item["status"] == "GRADED_LATE":
                g["late"] += 1

        g["points_earned"] += item["points_earned"]
        g["points_lost"] += item["points_lost"]

    for g in groups.values():
        g["points_earned"] = round(g["points_earned"], 2)
        g["points_lost"] = round(g["points_lost"], 2)
        settled = g["points_earned"] + g["points_lost"]
        if settled > 0:
            g["performance_pct"] = round(g["points_earned"] / settled * 100, 1)
        else:
            g["performance_pct"] = None

    return groups


def find_biggest_loss(groups):
    """Return the type that lost the most points, or None if nothing was lost."""
    lossy = {kind: g for kind, g in groups.items() if g["points_lost"] > 0}
    if not lossy:
        return None
    return max(lossy, key=lambda kind: lossy[kind]["points_lost"])


def build_breakdown(rows, today):
    """Put everything together: the list, the summary by type, the biggest loss."""
    items = list_assessments(rows, today)

    if not items:
        return {
            "status": "NO_ASSESSMENTS",
            "assessments": [],
            "by_type": {},
            "biggest_loss_type": None,
        }

    by_type = summarize_by_type(items)
    return {
        "status": "OK",
        "assessments": items,
        "by_type": by_type,
        "biggest_loss_type": find_biggest_loss(by_type),
    }



EXISTS_QUERY = "SELECT 1 FROM user_courses WHERE user_course_id = %s"

ASSESSMENTS_QUERY = """
    SELECT a.name, a.type, a.weight, a.max_score, a.due_date,
           s.score, s.submitted_at
    FROM user_courses uc
    JOIN assessments a ON a.course_id = uc.course_id
    LEFT JOIN assessment_submissions s
           ON s.assessment_id = a.assessment_id
          AND s.user_course_id = uc.user_course_id
    WHERE uc.user_course_id = %s
    ORDER BY a.due_date NULLS LAST, a.assessment_id
"""


def get_assessment_breakdown(user_course_id, today=None):
    """Fetch this student's assessments from the database and break them down."""
    today = today or date.today()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(EXISTS_QUERY, (user_course_id,))
            if cur.fetchone() is None:
                return {"status": "NOT_FOUND"}

            cur.execute(ASSESSMENTS_QUERY, (user_course_id,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return build_breakdown(rows, today)