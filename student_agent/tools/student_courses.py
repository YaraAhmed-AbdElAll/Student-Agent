from student_agent.db import get_connection

STUDENT_QUERY = "SELECT 1 FROM students WHERE student_id = %s"

COURSES_QUERY = """
    SELECT uc.user_course_id, c.course_id, c.name, c.type, c.credit_hours, uc.completed
    FROM user_courses uc
    JOIN courses c ON c.course_id = uc.course_id
    WHERE uc.student_id = %s
"""


def format_courses(rows):
    """Turn database rows into the list the agent will read.

    Each row is (user_course_id, course_id, name, kind, credit_hours, completed).
    Current courses come first, then completed ones, each group by name.
    """
    courses = []

    for user_course_id, course_id, name, kind, credit_hours, completed in rows:
        courses.append({
            "user_course_id": user_course_id,
            "course_id": course_id,
            "name": name,
            "type": kind,
            "credit_hours": credit_hours,
            "completed": bool(completed),
        })

    courses.sort(key=lambda c: (c["completed"], c["name"].lower()))

    if not courses:
        return {"status": "NO_COURSES", "courses": []}
    return {"status": "OK", "courses": courses}


def list_student_courses(student_id):
    """List every course the student is enrolled in, with its user_course_id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(STUDENT_QUERY, (student_id,))
            if cur.fetchone() is None:
                return {"status": "NOT_FOUND"}

            cur.execute(COURSES_QUERY, (student_id,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return format_courses(rows)