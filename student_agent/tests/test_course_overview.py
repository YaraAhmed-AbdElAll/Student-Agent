from datetime import date

from student_agent.tools import course_overview
from student_agent.tools.course_overview import compute_course_overview, sum_assessments

# Same default numbers for every test; each test changes only what it needs.
DEFAULTS = dict(final_max=50, pending_weight=0, final_score=None, days_to_final=30)


def run(**changes):
    return compute_course_overview(**{**DEFAULTS, **changes})


def test_final_minimum_is_the_binding_rule():
    r = run(pass_mark=50, midterm=10, assessments_earned=35)  # earned 45
    assert r["status"] == "OK"
    assert r["required_in_final"] == 20
    assert r["required_pct_of_final"] == 40.0
    assert r["binding_rule"] == "FINAL_MINIMUM"
    assert r["pass_still_possible"] is True


def test_total_is_the_binding_rule():
    r = run(pass_mark=50, midterm=8, assessments_earned=14)  # earned 22
    assert r["required_in_final"] == 28
    assert r["required_pct_of_final"] == 56.0
    assert r["binding_rule"] == "TOTAL"


def test_both_rules_equal():
    r = run(pass_mark=50, midterm=10, assessments_earned=20)  # earned 30
    assert r["required_in_final"] == 20
    assert r["binding_rule"] == "BOTH"


def test_pass_impossible():
    r = run(pass_mark=60, midterm=3, assessments_earned=2)  # earned 5, needs 55 of 50
    assert r["required_in_final"] == 55
    assert r["pass_still_possible"] is False


def test_missing_midterm():
    r = run(pass_mark=50, midterm=None, assessments_earned=10)
    assert r["status"] == "INSUFFICIENT_DATA"


def test_final_taken_below_minimum_fails():
    # total is 63 (enough) but the final paper is under 20
    r = run(pass_mark=50, midterm=10, assessments_earned=35, final_score=18)
    assert r["status"] == "FINAL_ALREADY_TAKEN"
    assert r["total"] == 63
    assert r["passed"] is False

TODAY = date(2026, 11, 1)


def test_graded_assessment_counts_by_weight():
    rows = [(5, 10, date(2026, 10, 1), 8)]  # 8/10 of weight 5 = 4
    assert sum_assessments(rows, TODAY) == (4.0, 0.0)


def test_missing_assessment_counts_zero_and_is_not_pending():
    rows = [(5, 10, date(2026, 10, 10), None)]  # due date passed, nothing submitted
    assert sum_assessments(rows, TODAY) == (0.0, 0.0)


def test_future_assessment_is_pending():
    rows = [(5, 10, date(2026, 12, 1), None)]  # not due yet
    assert sum_assessments(rows, TODAY) == (0.0, 5.0)


def test_mixed_assessments():
    rows = [
        (5, 10, date(2026, 10, 1), 8),     # earns 4.0
        (5, 10, date(2026, 10, 10), None), # missing -> 0
        (10, 20, date(2026, 12, 1), None), # pending 10
        (10, 20, date(2026, 10, 20), 15),  # 15/20 of 10 = 7.5
    ]
    assert sum_assessments(rows, TODAY) == (11.5, 10.0) 

def test_midterm_max_is_returned():
    r = run(pass_mark=50, midterm=None, assessments_earned=10, midterm_max=15)
    assert r["status"] == "INSUFFICIENT_DATA"
    assert r["midterm_max"] == 15       

class FakeCursor:
    """Stands in for a database cursor: returns prepared rows."""

    def __init__(self, course_row, assessment_rows):
        self.course_row = course_row
        self.assessment_rows = assessment_rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        pass

    def fetchone(self):
        return self.course_row

    def fetchall(self):
        return self.assessment_rows


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def close(self):
        pass


def test_coursework_max_is_returned():
    r = run(pass_mark=50, midterm=10, assessments_earned=35,
            midterm_max=15, coursework_max=50)
    assert r["status"] == "OK"
    assert r["coursework_max"] == 50
    assert r["earned_so_far"] == 45


def test_coursework_max_is_returned_when_midterm_is_missing():
    r = run(pass_mark=50, midterm=None, assessments_earned=10,
            midterm_max=15, coursework_max=50)
    assert r["status"] == "INSUFFICIENT_DATA"
    assert r["coursework_max"] == 50


def test_get_course_overview_reads_coursework_max(monkeypatch):
    # (pass_mark, final_max, exam_date, midterm, final, midterm_max, assessments_weight)
    course_row = (50, 50, date(2026, 12, 2), 6, None, 15, 35)
    cursor = FakeCursor(course_row, [])
    monkeypatch.setattr(course_overview, "get_connection", lambda: FakeConnection(cursor))

    r = course_overview.get_course_overview(1, today=date(2026, 11, 1))

    assert r["coursework_max"] == 50.0   # 35 from assessments + 15 midterm
    assert r["midterm_max"] == 15.0
    assert r["days_to_final"] == 31
    assert r["earned_so_far"] == 6.0


def test_coursework_max_is_unknown_without_midterm_max(monkeypatch):
    course_row = (50, 50, date(2026, 12, 2), 6, None, None, 35)
    cursor = FakeCursor(course_row, [])
    monkeypatch.setattr(course_overview, "get_connection", lambda: FakeConnection(cursor))

    r = course_overview.get_course_overview(1, today=date(2026, 11, 1))
    assert r["coursework_max"] is None    

def test_course_total_is_ok_when_it_adds_up_to_100():
    r = run(pass_mark=50, midterm=10, assessments_earned=35,
            midterm_max=15, coursework_max=50)  # 50 + 50 = 100
    assert r["course_total"] == 100
    assert r["course_total_ok"] is True


def test_course_total_not_ok_when_it_does_not_add_up():
    r = run(pass_mark=50, midterm=10, assessments_earned=35,
            midterm_max=15, coursework_max=45)  # 45 + 50 = 95
    assert r["course_total"] == 95
    assert r["course_total_ok"] is False
    assert r["status"] == "OK"  # a warning only, the calculation still runs


def test_course_total_is_unknown_without_coursework_max():
    r = run(pass_mark=50, midterm=10, assessments_earned=35)
    assert r["course_total"] is None
    assert r["course_total_ok"] is None


def test_get_course_overview_flags_a_bad_total(monkeypatch):
    # assessments weigh 30 and the midterm 15, so coursework is 45 and the course 95
    course_row = (50, 50, date(2026, 12, 2), 6, None, 15, 30)
    cursor = FakeCursor(course_row, [])
    monkeypatch.setattr(course_overview, "get_connection", lambda: FakeConnection(cursor))

    r = course_overview.get_course_overview(1, today=date(2026, 11, 1))
    assert r["coursework_max"] == 45.0
    assert r["course_total"] == 95.0
    assert r["course_total_ok"] is False