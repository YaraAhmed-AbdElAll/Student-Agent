from student_agent.db import get_connection

OWNS_QUERY = """
    SELECT 1 FROM user_courses
    WHERE user_course_id = %s AND student_id = %s
"""


def get_student_id(config):
    """Read the logged-in student's id from the config the app passes in."""
    if not config:
        return None
    return config.get("configurable", {}).get("student_id")


def owns_course(student_id, user_course_id):
    """True only if this enrollment belongs to this student."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(OWNS_QUERY, (user_course_id, student_id))
            return cur.fetchone() is not None
    finally:
        conn.close()