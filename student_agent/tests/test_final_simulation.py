from student_agent.tools import final_simulation
from student_agent.tools.course_overview import compute_course_overview
from student_agent.tools.final_simulation import compute_simulation


def overview(earned=40, pending=0, **changes):
    """A real overview. 'earned' is what the student has before the final."""
    args = dict(
        pass_mark=50, final_max=50, midterm=10, assessments_earned=earned - 10,
        pending_weight=pending, final_score=None, days_to_final=30,
    )
    args.update(changes)
    return compute_course_overview(**args)


def simulate(hypothetical, earned=40, pending=0, **changes):
    return compute_simulation(overview(earned, pending, **changes), hypothetical)


def test_pass_guaranteed():
    r = simulate(35)  # 40 + 35 = 75
    assert r["status"] == "OK"
    assert r["outcome"] == "PASS_GUARANTEED"
    assert r["margin_over_pass"] == 25
    assert r["failed_rule"] is None


def test_pass_exactly_at_the_limit():
    r = simulate(28, earned=22)  # 22 + 28 = 50
    assert r["outcome"] == "PASS_GUARANTEED"
    assert r["margin_over_pass"] == 0


def test_final_minimum_fail():
    r = simulate(15)  # total is 55 but the final paper is under 20
    assert r["outcome"] == "FAIL_GUARANTEED"
    assert r["failed_rule"] == "FINAL_MINIMUM"
    assert r["final_points_short"] == 5
    assert r["points_short"] is None


def test_total_fail():
    r = simulate(25, earned=22)  # 47
    assert r["outcome"] == "FAIL_GUARANTEED"
    assert r["failed_rule"] == "TOTAL"
    assert r["points_short"] == 3
    assert r["final_points_short"] is None


def test_both_fail():
    r = simulate(15, earned=22)  # 37 and under 20
    assert r["failed_rule"] == "BOTH"
    assert r["points_short"] == 13
    assert r["final_points_short"] == 5


def test_final_exactly_at_minimum_counts():
    r = simulate(20, earned=45)
    assert r["outcome"] == "PASS_GUARANTEED"
    assert r["margin_over_pass"] == 15


def test_pending_cannot_fix_final_minimum():
    r = simulate(19, earned=40, pending=5)
    assert r["outcome"] == "FAIL_GUARANTEED"
    assert r["failed_rule"] == "FINAL_MINIMUM"
    assert r["final_points_short"] == 1


def test_depends_on_pending_work():
    r = simulate(25, earned=22, pending=5)  # between 47 and 52
    assert r["outcome"] == "DEPENDS"
    assert r["needed_from_pending"] == 3
    assert r["total_if_pending_zero"] == 47
    assert r["total_if_pending_full"] == 52


def test_depends_needs_full_marks_in_pending():
    r = simulate(25, earned=22, pending=3)  # best case is exactly 50
    assert r["outcome"] == "DEPENDS"
    assert r["needed_from_pending"] == 3


def test_fail_even_with_full_pending():
    r = simulate(20, earned=22, pending=5)  # best case is 47
    assert r["outcome"] == "FAIL_GUARANTEED"
    assert r["failed_rule"] == "TOTAL"
    assert r["points_short"] == 3


def test_invalid_inputs():
    for bad in (-1, 60, "abc", True, None, float("nan")):
        r = simulate(bad)
        assert r == {"status": "INVALID_INPUT", "allowed_min": 0, "allowed_max": 50}


def test_boundaries_are_valid():
    assert simulate(0)["status"] == "OK"
    assert simulate(50)["status"] == "OK"


def test_midterm_not_recorded():
    assert simulate(30, midterm=None) == {"status": "MIDTERM_NOT_RECORDED"}


def test_final_already_taken():
    r = simulate(30, final_score=40)
    assert r["status"] == "FINAL_ALREADY_TAKEN"
    assert r["final_score"] == 40
    assert r["total"] == 80
    assert r["passed"] is True


def test_config_error_passes_through():
    assert simulate(30, final_max=15) == {"status": "INVALID_CONFIG"}


def test_not_found_passes_through():
    assert compute_simulation({"status": "NOT_FOUND"}, 30) == {"status": "NOT_FOUND"}


def test_wrapper_uses_the_overview(monkeypatch):
    fake = overview(earned=40)
    monkeypatch.setattr(
        final_simulation, "get_course_overview",
        lambda user_course_id, today=None: fake,
    )
    r = final_simulation.simulate_final_score(1, 35)
    assert r["outcome"] == "PASS_GUARANTEED"