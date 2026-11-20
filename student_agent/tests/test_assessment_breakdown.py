from datetime import date, datetime

from student_agent.tools.assessment_breakdown import (
    build_breakdown,
    classify_assessment,
    list_assessments,
)

TODAY = date(2026, 11, 1)


def one(**changes):
    args = dict(
        name="Quiz 1", kind="quiz", weight=5, max_score=10,
        due_date=date(2026, 10, 1), score=None, submitted_at=None, today=TODAY,
    )
    args.update(changes)
    return classify_assessment(**args)


def test_graded_on_time():
    r = one(score=8, submitted_at=datetime(2026, 10, 1, 9, 0))
    assert r["status"] == "GRADED"
    assert r["pct"] == 80.0
    assert r["points_earned"] == 4.0
    assert r["points_lost"] == 1.0


def test_graded_late():
    r = one(score=6, submitted_at=datetime(2026, 10, 3, 22, 0))
    assert r["status"] == "GRADED_LATE"
    assert r["points_earned"] == 3.0
    assert r["points_lost"] == 2.0


def test_missing():
    r = one(due_date=date(2026, 10, 10))
    assert r["status"] == "MISSING"
    assert r["pct"] is None
    assert r["points_earned"] == 0.0
    assert r["points_lost"] == 5.0


def test_pending():
    r = one(due_date=date(2026, 12, 1))
    assert r["status"] == "PENDING"
    assert r["points_lost"] is None


def test_list_keeps_every_row():
    rows = [
        ("Quiz 1", "quiz", 5, 10, date(2026, 10, 1), 8, datetime(2026, 10, 1, 9, 0)),
        ("Quiz 2", "quiz", 5, 10, date(2026, 10, 10), None, None),
        ("Quiz 3", "quiz", 5, 10, date(2026, 12, 1), None, None),
    ]
    statuses = [item["status"] for item in list_assessments(rows, TODAY)]
    assert statuses == ["GRADED", "MISSING", "PENDING"]

ROWS = [
    ("Quiz 1", "quiz", 5, 10, date(2026, 10, 1), 8, datetime(2026, 10, 1, 9, 0)),
    ("Quiz 2", "quiz", 5, 10, date(2026, 10, 10), None, None),
    ("Assignment 1", "assignment", 10, 10, date(2026, 10, 15), 5, datetime(2026, 10, 14, 10, 0)),
    ("Assignment 2", "assignment", 10, 10, date(2026, 12, 1), None, None),
    ("Oral", "oral", 5, 5, date(2026, 10, 20), 5, datetime(2026, 10, 20, 8, 0)),
]


def test_quiz_summary():
    quiz = build_breakdown(ROWS, TODAY)["by_type"]["quiz"]
    assert quiz["count"] == 2
    assert quiz["graded"] == 1
    assert quiz["missing"] == 1
    assert quiz["points_earned"] == 4.0
    assert quiz["points_lost"] == 6.0
    assert quiz["performance_pct"] == 40.0


def test_pending_is_counted_but_not_summed():
    assignment = build_breakdown(ROWS, TODAY)["by_type"]["assignment"]
    assert assignment["count"] == 2
    assert assignment["pending"] == 1
    assert assignment["points_earned"] == 5.0
    assert assignment["points_lost"] == 5.0


def test_biggest_loss_type():
    assert build_breakdown(ROWS, TODAY)["biggest_loss_type"] == "quiz"


def test_no_losses_gives_none():
    rows = [("Oral", "oral", 5, 5, date(2026, 10, 20), 5, datetime(2026, 10, 20, 8, 0))]
    result = build_breakdown(rows, TODAY)
    assert result["by_type"]["oral"]["performance_pct"] == 100.0
    assert result["biggest_loss_type"] is None


def test_late_is_counted():
    rows = [("A1", "assignment", 10, 10, date(2026, 10, 1), 6, datetime(2026, 10, 3, 22, 0))]
    g = build_breakdown(rows, TODAY)["by_type"]["assignment"]
    assert g["graded"] == 1
    assert g["late"] == 1
    assert g["points_lost"] == 4.0


def test_empty_list():
    result = build_breakdown([], TODAY)
    assert result["status"] == "NO_ASSESSMENTS"
    assert result["by_type"] == {}    