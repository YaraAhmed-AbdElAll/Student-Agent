import inspect

from student_agent import graph as graph_module
from student_agent.prompts import SYSTEM_PROMPT
from student_agent.tools import (
    course_overview,
    final_simulation,
    risk_assessment,
    student_courses,
)

# Every field the prompt talks about must really exist in the tool that returns it.
# If someone renames a field in a tool, this test fails and reminds us to update the prompt.
FIELDS = {
    "required_in_final": course_overview,
    "binding_rule": course_overview,
    "pass_still_possible": course_overview,
    "outcome": final_simulation,
    "needed_from_pending": final_simulation,
    "failed_rule": final_simulation,
    "risk_level": risk_assessment,
    "escalated_by_time": risk_assessment,
    "midterm_scenarios": risk_assessment,
    "data_gaps": risk_assessment,
    "completed": student_courses,
    "coursework_max": course_overview,
    "total_if_pending_zero": final_simulation,
    "total_if_pending_full": final_simulation,
    "points_short": final_simulation,
    "final_points_short": final_simulation,
    "course_total_ok": course_overview,
    "course_total": course_overview,
}

GAP_CODES = [
    "MIDTERM_NOT_RECORDED",
    "FINAL_RESULT_NOT_RECORDED",
    "NOT_ENOUGH_GRADES_FOR_TREND",
    "NO_ATTENDANCE_DATA",
    "COURSE_TOTAL_MISMATCH"
]


def test_graph_uses_the_real_prompt_by_default():
    assert graph_module.SYSTEM_PROMPT == SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) > 500


def test_prompt_only_names_fields_that_exist():
    for field, module in FIELDS.items():
        assert field in SYSTEM_PROMPT, field
        assert f'"{field}"' in inspect.getsource(module), field


def test_prompt_covers_every_data_gap():
    source = inspect.getsource(risk_assessment)
    for code in GAP_CODES:
        assert code in source, code
        assert code in SYSTEM_PROMPT, code

def test_prompt_keeps_its_main_rules():
    for phrase in ("LATEST message", "General advice:", "Egyptian", "which measure"):
        assert phrase in SYSTEM_PROMPT, phrase