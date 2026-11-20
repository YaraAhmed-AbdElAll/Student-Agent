from datetime import date

from student_agent.tools import risk_assessment
from student_agent.tools.assessment_breakdown import build_breakdown
from student_agent.tools.attendance_detail import build_attendance
from student_agent.tools.course_overview import compute_course_overview
from student_agent.tools.missing_work import find_missing_work
from student_agent.tools.performance_trend import compute_trend
from student_agent.tools.risk_assessment import compute_risk

TODAY = date(2026, 11, 1)


# Each helper builds a REAL tool result, so the tools are tested together.
def overview_of(earned=45, **changes):
    args = dict(
        pass_mark=50, final_max=50, midterm=10, assessments_earned=earned - 10,
        pending_weight=0, final_score=None, days_to_final=60,
    )
    args.update(changes)
    return compute_course_overview(**args)


def trend_of(*pcts):
    items = [
        {"name": f"T{n}", "due_date": f"2026-10-{n:02d}", "pct": p, "status": "GRADED"}
        for n, p in enumerate(pcts, start=1)
    ]
    return compute_trend(items)


def attendance_of(absent):
    rows = [
        (f"Lecture {n}", date(2026, 10, n), f"Topic {n}", n not in absent)
        for n in range(1, 11)
    ]
    return build_attendance(rows, None, TODAY)


def missing_of(*weights):
    rows = [
        (f"Quiz {i}", "quiz", w, 10, date(2026, 10, i), None, None)
        for i, w in enumerate(weights, start=1)
    ]
    return find_missing_work(build_breakdown(rows, TODAY)["assessments"], TODAY)


def risk(overview=None, trend=None, attendance=None, missing=None):
    """A student with no problems, unless a tool result is replaced."""
    return compute_risk(
        overview if overview is not None else overview_of(),
        trend if trend is not None else trend_of(70, 70, 70, 70),
        attendance if attendance is not None else attendance_of([]),
        missing if missing is not None else missing_of(),
    )


def codes(result):
    return [e["code"] for e in result["evidence"]]


def test_quiet_student_is_low():
    r = risk()
    assert r["status"] == "OK"
    assert r["risk_level"] == "LOW"
    assert r["evidence"] == []
    assert r["data_gaps"] == []
    assert r["escalated_by_time"] is False


def test_pass_impossible_is_high():
    r = risk(overview=overview_of(pass_mark=60, midterm=3, assessments_earned=2))
    assert r["risk_level"] == "HIGH"
    assert codes(r) == ["PASS_IMPOSSIBLE"]
    assert r["evidence"][0]["facts"]["required_in_final"] == 55


def test_final_requirement_60_is_medium():
    r = risk(overview=overview_of(midterm=8, assessments_earned=12))  # earned 20
    assert r["risk_level"] == "MEDIUM"
    assert codes(r) == ["HIGH_FINAL_REQUIREMENT"]
    assert r["evidence"][0]["facts"]["required_pct_of_final"] == 60.0


def test_final_requirement_80_is_high():
    r = risk(overview=overview_of(midterm=5, assessments_earned=5))  # earned 10
    assert r["risk_level"] == "HIGH"
    assert r["evidence"][0]["facts"]["required_pct_of_final"] == 80.0


def test_trend_down_is_medium():
    r = risk(trend=trend_of(90, 70, 50, 30))
    assert r["risk_level"] == "MEDIUM"
    assert codes(r) == ["TREND_DOWN"]
    assert r["evidence"][0]["facts"]["change_pct_points"] == -40.0


def test_attendance_70_is_medium():
    r = risk(attendance=attendance_of([3, 7, 9]))
    assert r["risk_level"] == "MEDIUM"
    assert codes(r) == ["LOW_ATTENDANCE"]
    assert r["evidence"][0]["facts"]["attendance_pct"] == 70.0


def test_attendance_40_is_high():
    r = risk(attendance=attendance_of([1, 2, 4, 6, 8, 10]))
    assert r["risk_level"] == "HIGH"
    assert codes(r) == ["LOW_ATTENDANCE"]


def test_attendance_exactly_50_is_medium():
    r = risk(attendance=attendance_of([1, 2, 3, 4, 5]))
    assert r["risk_level"] == "MEDIUM"


def test_absence_streak():
    r = risk(attendance=attendance_of([8, 9, 10]))
    assert codes(r) == ["LOW_ATTENDANCE", "ABSENCE_STREAK"]
    assert r["evidence"][1]["facts"]["current_absence_streak"] == 3


def test_missing_work_boundaries():
    assert codes(risk(missing=missing_of(5, 4))) == []  # 9 points
    assert risk(missing=missing_of(5, 5))["risk_level"] == "MEDIUM"  # 10 points
    high = risk(missing=missing_of(10, 10))  # 20 points
    assert high["risk_level"] == "HIGH"
    assert codes(high) == ["MISSING_WORK"]
    assert high["evidence"][0]["facts"]["missing_count"] == 2


def test_highest_level_wins_and_evidence_is_sorted():
    r = risk(trend=trend_of(90, 70, 50, 30), missing=missing_of(10, 10))
    assert r["risk_level"] == "HIGH"
    assert codes(r) == ["MISSING_WORK", "TREND_DOWN"]


def test_time_escalates_medium_to_high():
    r = risk(overview=overview_of(days_to_final=10), trend=trend_of(90, 70, 50, 30))
    assert r["risk_level"] == "HIGH"
    assert r["escalated_by_time"] is True
    assert r["days_to_final"] == 10


def test_exam_14_days_away_is_not_urgent():
    r = risk(overview=overview_of(days_to_final=14), trend=trend_of(90, 70, 50, 30))
    assert r["risk_level"] == "MEDIUM"
    assert r["escalated_by_time"] is False


def test_time_alone_is_not_risk():
    r = risk(overview=overview_of(days_to_final=3))
    assert r["risk_level"] == "LOW"
    assert r["escalated_by_time"] is False


def test_high_is_not_escalated():
    r = risk(overview=overview_of(days_to_final=3), missing=missing_of(10, 10))
    assert r["risk_level"] == "HIGH"
    assert r["escalated_by_time"] is False


def test_midterm_missing_gives_unknown():
    r = risk(overview=overview_of(midterm=None))
    assert r["risk_level"] == "UNKNOWN"
    assert r["data_gaps"] == ["MIDTERM_NOT_RECORDED"]


def test_midterm_missing_with_other_evidence():
    r = risk(
        overview=overview_of(midterm=None),
        attendance=attendance_of([1, 2, 4, 6, 8, 10]),
    )
    assert r["risk_level"] == "HIGH"
    assert "MIDTERM_NOT_RECORDED" in r["data_gaps"]


def test_result_not_recorded_is_a_gap_not_unknown():
    r = risk(overview=overview_of(days_to_final=-5))
    assert r["risk_level"] == "LOW"
    assert r["data_gaps"] == ["FINAL_RESULT_NOT_RECORDED"]
    assert r["escalated_by_time"] is False


def test_few_grades_is_a_gap_not_risk():
    r = risk(trend=trend_of(70, 80))
    assert r["risk_level"] == "LOW"
    assert r["data_gaps"] == ["NOT_ENOUGH_GRADES_FOR_TREND"]


def test_no_lectures_is_a_gap():
    r = risk(attendance=build_attendance([], None, TODAY))
    assert r["risk_level"] == "LOW"
    assert r["data_gaps"] == ["NO_ATTENDANCE_DATA"]


def test_final_already_taken():
    r = risk(overview=overview_of(final_score=40))
    assert r == {"status": "FINAL_ALREADY_TAKEN", "total": 85, "passed": True}


def test_not_found_passes_through():
    assert risk(overview={"status": "NOT_FOUND"}) == {"status": "NOT_FOUND"}
    assert risk(attendance={"status": "NOT_FOUND"}) == {"status": "NOT_FOUND"}


def test_invalid_config_passes_through():
    assert risk(overview=overview_of(final_max=15)) == {"status": "INVALID_CONFIG"}


def test_exam_bar_is_off_by_default():
    r = risk(attendance=attendance_of([1, 2, 4, 6, 8, 10]))
    assert "EXAM_BAR_RISK" not in codes(r)


def test_exam_bar_when_configured(monkeypatch):
    monkeypatch.setattr(risk_assessment, "ATTENDANCE_BAR_PCT", 60)
    r = risk(attendance=attendance_of([1, 2, 4, 6, 8, 10]))  # 40% attendance
    assert "EXAM_BAR_RISK" in codes(r)


def test_wrapper_combines_the_four_tools(monkeypatch):
    monkeypatch.setattr(
        risk_assessment, "get_course_overview", lambda uc, today=None: overview_of()
    )
    monkeypatch.setattr(
        risk_assessment, "get_performance_trend",
        lambda uc, today=None: trend_of(90, 70, 50, 30),
    )
    monkeypatch.setattr(
        risk_assessment, "get_attendance_detail",
        lambda uc, today=None: attendance_of([]),
    )
    monkeypatch.setattr(
        risk_assessment, "get_missing_work", lambda uc, today=None: missing_of()
    )
    r = risk_assessment.get_risk_assessment(1)
    assert codes(r) == ["TREND_DOWN"]


def test_midterm_missing_but_it_changes_nothing():
    r = risk(overview=overview_of(midterm=None, midterm_max=15))  # 35 from coursework
    assert r["risk_level"] == "LOW"
    assert r["risk_range"] is None
    assert r["data_gaps"] == ["MIDTERM_NOT_RECORDED"]
    s = r["midterm_scenarios"]
    assert s["if_midterm_zero"]["required_in_final"] == 20
    assert s["if_midterm_full"]["required_in_final"] == 20


def test_midterm_missing_and_it_decides_the_level():
    # coursework 10: midterm 0 -> needs 40 (80%), midterm 15 -> needs 25 (50%)
    r = risk(overview=overview_of(midterm=None, midterm_max=15, assessments_earned=10))
    assert r["risk_level"] == "RANGE"
    assert r["risk_range"] == {"best_case": "LOW", "worst_case": "HIGH"}
    s = r["midterm_scenarios"]
    assert s["if_midterm_zero"]["required_in_final"] == 40
    assert s["if_midterm_zero"]["required_pct_of_final"] == 80.0
    assert s["if_midterm_full"]["required_in_final"] == 25
    assert s["if_midterm_full"]["required_pct_of_final"] == 50.0
    assert r["evidence"] == []


def test_other_evidence_sets_a_floor_under_the_range():
    r = risk(
        overview=overview_of(midterm=None, midterm_max=15, assessments_earned=10),
        attendance=attendance_of([1, 2, 4, 6, 8, 10]),  # 40% attendance
    )
    assert r["risk_level"] == "HIGH"
    assert r["risk_range"] is None
    assert codes(r) == ["LOW_ATTENDANCE"]


def test_time_escalation_is_decided_per_scenario():
    # coursework 15: midterm 0 -> needs 35 (70%, MEDIUM); midterm 15 -> needs 20 (LOW)
    r = risk(overview=overview_of(
        midterm=None, midterm_max=15, assessments_earned=15, days_to_final=10,
    ))
    s = r["midterm_scenarios"]
    assert s["if_midterm_zero"]["risk_level"] == "HIGH"  # raised from MEDIUM by time
    assert s["if_midterm_zero"]["escalated_by_time"] is True
    assert s["if_midterm_full"]["risk_level"] == "LOW"
    assert r["risk_range"] == {"best_case": "LOW", "worst_case": "HIGH"}
    assert r["escalated_by_time"] is False    

def test_bad_course_total_is_a_gap_not_risk():
    r = risk(overview=overview_of(coursework_max=45, midterm_max=15))
    assert r["risk_level"] == "LOW"
    assert r["evidence"] == []
    assert r["data_gaps"] == ["COURSE_TOTAL_MISMATCH"]


def test_good_course_total_has_no_gap():
    r = risk(overview=overview_of(coursework_max=50, midterm_max=15))
    assert r["data_gaps"] == []
