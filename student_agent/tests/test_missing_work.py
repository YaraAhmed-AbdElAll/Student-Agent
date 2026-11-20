from datetime import date, datetime

from student_agent.tools import missing_work
from student_agent.tools.assessment_breakdown import build_breakdown
from student_agent.tools.missing_work import find_missing_work

TODAY = date(2026, 11, 1)

ROWS = [
    ("Quiz 1", "quiz", 5, 10, date(2026, 10, 1), 8, datetime(2026, 10, 1, 9, 0)),
    ("Quiz 2", "quiz", 5, 10, date(2026, 10, 10), None, None),
    ("Assignment 1", "assignment", 10, 10, date(2026, 10, 15), 5, datetime(2026, 10, 17, 10, 0)),
    ("Assignment 2", "assignment", 10, 10, date(2026, 10, 22), None, None),
    ("Project", "project", 15, 100, date(2026, 12, 1), None, None),
    ("Oral", "oral", 5, 5, date(2026, 11, 15), None, None),
    ("Practical", "practical", 5, 10, None, None, None),
]


def analyse(rows):
    # Build the items with the real breakdown code, so both tools are tested together.
    return find_missing_work(build_breakdown(rows, TODAY)["assessments"], TODAY)


def test_missing_sorted_by_points_lost_and_summed():
    r = analyse(ROWS)
    assert r["missing_count"] == 2
    assert [m["name"] for m in r["missing"]] == ["Assignment 2", "Quiz 2"]
    assert r["missing_points_lost"] == 15.0


def test_days_overdue():
    r = analyse(ROWS)
    days = {m["name"]: m["days_overdue"] for m in r["missing"]}
    assert days == {"Quiz 2": 22, "Assignment 2": 10}


def test_late_work_is_listed():
    r = analyse(ROWS)
    assert r["late_count"] == 1
    assert r["late"][0]["name"] == "Assignment 1"
    assert r["late"][0]["pct"] == 50.0


def test_upcoming_sorted_with_no_date_last():
    r = analyse(ROWS)
    assert [u["name"] for u in r["upcoming"]] == ["Oral", "Project", "Practical"]
    assert r["upcoming"][0]["days_left"] == 14
    assert r["upcoming"][1]["days_left"] == 30
    assert r["upcoming"][2]["days_left"] is None


def test_on_time_work_appears_nowhere():
    r = analyse(ROWS)
    names = [x["name"] for x in r["missing"] + r["late"] + r["upcoming"]]
    assert "Quiz 1" not in names


def test_due_today_counts_as_missing():
    r = analyse([("Quiz", "quiz", 5, 10, TODAY, None, None)])
    assert r["missing_count"] == 1
    assert r["missing"][0]["days_overdue"] == 0


def test_nothing_wrong():
    rows = [("Quiz 1", "quiz", 5, 10, date(2026, 10, 1), 8, datetime(2026, 10, 1, 9, 0))]
    r = analyse(rows)
    assert r["status"] == "OK"
    assert r["missing_count"] == 0
    assert r["missing_points_lost"] == 0
    assert r["late_count"] == 0
    assert r["upcoming"] == []


def test_wrapper_passes_through_not_found(monkeypatch):
    monkeypatch.setattr(
        missing_work, "get_assessment_breakdown",
        lambda user_course_id, today=None: {"status": "NOT_FOUND"},
    )
    assert missing_work.get_missing_work(999) == {"status": "NOT_FOUND"}


def test_wrapper_passes_through_no_assessments(monkeypatch):
    monkeypatch.setattr(
        missing_work, "get_assessment_breakdown",
        lambda user_course_id, today=None: {"status": "NO_ASSESSMENTS", "assessments": []},
    )
    assert missing_work.get_missing_work(1) == {"status": "NO_ASSESSMENTS"}