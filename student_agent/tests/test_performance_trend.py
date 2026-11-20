from student_agent.tools.performance_trend import compute_trend
from student_agent.tools import performance_trend


def item(name, due, pct, status="GRADED"):
    return {"name": name, "due_date": due, "pct": pct, "status": status}


def graded(*pcts):
    """Build graded items T1, T2, ... one day apart from the given percentages."""
    return [
        item(f"T{n}", f"2026-10-{n:02d}", pct)
        for n, pct in enumerate(pcts, start=1)
    ]


def test_downward():
    r = compute_trend(graded(90, 70, 50, 30))
    assert r["direction"] == "DOWN"
    assert r["earlier_avg_pct"] == 80.0
    assert r["recent_avg_pct"] == 40.0
    assert r["change_pct_points"] == -40.0
    assert r["biggest_drop"]["change"] == -20.0


def test_upward_has_no_drop():
    r = compute_trend(graded(40, 50, 70, 90))
    assert r["direction"] == "UP"
    assert r["biggest_drop"] is None


def test_flat():
    r = compute_trend(graded(70, 72, 69, 71))
    assert r["direction"] == "FLAT"
    assert r["biggest_drop"] == {"from": "T2", "to": "T3", "change": -3.0}


def test_three_points_is_enough():
    r = compute_trend(graded(80, 60, 40))
    assert r["status"] == "OK"
    assert r["direction"] == "DOWN"


def test_too_few_points():
    r = compute_trend(graded(80, 60))
    assert r["status"] == "INSUFFICIENT_DATA"
    assert r["points"] == 2


def test_missing_and_pending_are_ignored():
    items = graded(90, 70, 50) + [
        item("M", "2026-10-20", None, status="MISSING"),
        item("P", "2026-12-01", None, status="PENDING"),
    ]
    r = compute_trend(items)
    assert len(r["series"]) == 3


def test_sorted_by_date():
    items = [
        item("B", "2026-10-02", 50),
        item("A", "2026-10-01", 90),
        item("C", "2026-10-03", 30),
    ]
    r = compute_trend(items)
    assert [p["name"] for p in r["series"]] == ["A", "B", "C"]


def test_threshold_is_inclusive():
    r = compute_trend(graded(70, 70, 80, 80))
    assert r["change_pct_points"] == 10.0
    assert r["direction"] == "UP"

def test_wrapper_uses_the_breakdown_result(monkeypatch):
    fake = {"status": "OK", "assessments": graded(90, 70, 50, 30)}
    monkeypatch.setattr(
        performance_trend, "get_assessment_breakdown",
        lambda user_course_id, today=None: fake,
    )
    r = performance_trend.get_performance_trend(1)
    assert r["direction"] == "DOWN"


def test_wrapper_passes_through_not_found(monkeypatch):
    monkeypatch.setattr(
        performance_trend, "get_assessment_breakdown",
        lambda user_course_id, today=None: {"status": "NOT_FOUND"},
    )
    assert performance_trend.get_performance_trend(999) == {"status": "NOT_FOUND"}    