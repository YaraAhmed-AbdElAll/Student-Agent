import pytest

from student_agent.access import get_student_id
from student_agent.tools import langchain_tools as lt

# (tool, name of the function it calls inside langchain_tools, what the model sends)
GUARDED = [
    (lt.course_overview_tool, "get_course_overview", {"user_course_id": 5}),
    (lt.assessment_breakdown_tool, "get_assessment_breakdown", {"user_course_id": 5}),
    (lt.performance_trend_tool, "get_performance_trend", {"user_course_id": 5}),
    (lt.attendance_detail_tool, "get_attendance_detail", {"user_course_id": 5}),
    (lt.missing_work_tool, "get_missing_work", {"user_course_id": 5}),
    (lt.final_simulation_tool, "simulate_final_score",
     {"user_course_id": 5, "hypothetical_final": 30}),
    (lt.risk_assessment_tool, "get_risk_assessment", {"user_course_id": 5}),
]
IDS = [g[1] for g in GUARDED]

LOGGED_IN = {"configurable": {"student_id": 1}}
NOT_LOGGED_IN = {"configurable": {}}


def must_not_run(*args):
    raise AssertionError("this must not run")


def test_get_student_id_reads_the_config():
    assert get_student_id(None) is None
    assert get_student_id({}) is None
    assert get_student_id({"configurable": {}}) is None
    assert get_student_id({"configurable": {"student_id": 7}}) == 7


def test_all_eight_tools_are_registered():
    names = {t.name for t in lt.ALL_TOOLS}
    assert names == {
        "list_student_courses", "get_course_overview", "get_assessment_breakdown",
        "get_performance_trend", "get_attendance_detail", "get_missing_work",
        "simulate_final_score", "get_risk_assessment",
    }
    assert len(lt.ALL_TOOLS) == 8


def test_the_model_never_sees_student_id_or_config():
    for t in lt.ALL_TOOLS:
        assert "student_id" not in t.args
        assert "config" not in t.args


def test_the_model_only_sends_what_it_should():
    sent = {t.name: set(t.args) for t in lt.ALL_TOOLS}
    assert sent["list_student_courses"] == set()
    assert sent["simulate_final_score"] == {"user_course_id", "hypothetical_final"}
    others = [n for n in sent if n not in ("list_student_courses", "simulate_final_score")]
    for name in others:
        assert sent[name] == {"user_course_id"}


def test_every_tool_has_a_real_description():
    for t in lt.ALL_TOOLS:
        assert len(t.description) > 60


def test_ownership_check_uses_the_logged_in_student(monkeypatch):
    seen = {}

    def fake_owns(student_id, user_course_id):
        seen["pair"] = (student_id, user_course_id)
        return True

    monkeypatch.setattr(lt, "owns_course", fake_owns)
    monkeypatch.setattr(lt, "get_course_overview", lambda *a: {"status": "OK"})
    lt.course_overview_tool.invoke(
        {"user_course_id": 5}, config={"configurable": {"student_id": 9}}
    )
    assert seen["pair"] == (9, 5)


@pytest.mark.parametrize("tool, func_name, args", GUARDED, ids=IDS)
def test_owned_course_reaches_the_function(monkeypatch, tool, func_name, args):
    monkeypatch.setattr(lt, "owns_course", lambda student_id, user_course_id: True)
    monkeypatch.setattr(lt, func_name, lambda *a: {"status": "OK", "called_with": a})
    result = tool.invoke(args, config=LOGGED_IN)
    assert result["status"] == "OK"
    assert result["called_with"][0] == 5


@pytest.mark.parametrize("tool, func_name, args", GUARDED, ids=IDS)
def test_someone_elses_course_is_blocked(monkeypatch, tool, func_name, args):
    monkeypatch.setattr(lt, "owns_course", lambda student_id, user_course_id: False)
    monkeypatch.setattr(lt, func_name, must_not_run)
    assert tool.invoke(args, config=LOGGED_IN) == {"status": "NOT_YOURS"}


@pytest.mark.parametrize("tool, func_name, args", GUARDED, ids=IDS)
def test_no_login_is_blocked(monkeypatch, tool, func_name, args):
    monkeypatch.setattr(lt, "owns_course", must_not_run)
    monkeypatch.setattr(lt, func_name, must_not_run)
    assert tool.invoke(args, config=NOT_LOGGED_IN) == {"status": "NOT_LOGGED_IN"}


def test_list_courses_uses_the_logged_in_student(monkeypatch):
    monkeypatch.setattr(
        lt, "list_student_courses", lambda student_id: {"status": "OK", "for": student_id}
    )
    result = lt.list_courses_tool.invoke({}, config={"configurable": {"student_id": 9}})
    assert result == {"status": "OK", "for": 9}


def test_list_courses_needs_login(monkeypatch):
    monkeypatch.setattr(lt, "list_student_courses", must_not_run)
    assert lt.list_courses_tool.invoke({}, config=NOT_LOGGED_IN) == {"status": "NOT_LOGGED_IN"}