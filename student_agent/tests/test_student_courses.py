from student_agent.tools.student_courses import format_courses


def test_returns_all_fields():
    rows = [(12, 3, "Data Structures", "specialized", 3, False)]
    r = format_courses(rows)
    assert r["status"] == "OK"
    assert r["courses"] == [{
        "user_course_id": 12,
        "course_id": 3,
        "name": "Data Structures",
        "type": "specialized",
        "credit_hours": 3,
        "completed": False,
    }]


def test_current_courses_first_then_alphabetical():
    rows = [
        (1, 1, "Zoology", "general", 2, True),
        (2, 2, "Linear Algebra", "general", 3, False),
        (3, 3, "algorithms", "specialized", 3, True),
        (4, 4, "Data Structures", "specialized", 3, False),
    ]
    names = [c["name"] for c in format_courses(rows)["courses"]]
    assert names == ["Data Structures", "Linear Algebra", "algorithms", "Zoology"]


def test_null_completed_means_current():
    rows = [(1, 1, "Data Structures", "specialized", 3, None)]
    assert format_courses(rows)["courses"][0]["completed"] is False


def test_no_courses():
    assert format_courses([]) == {"status": "NO_COURSES", "courses": []}