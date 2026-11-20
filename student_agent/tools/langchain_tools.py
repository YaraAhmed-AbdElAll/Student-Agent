from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from student_agent.access import get_student_id, owns_course
from student_agent.tools.assessment_breakdown import get_assessment_breakdown
from student_agent.tools.attendance_detail import get_attendance_detail
from student_agent.tools.course_overview import get_course_overview
from student_agent.tools.final_simulation import simulate_final_score
from student_agent.tools.missing_work import get_missing_work
from student_agent.tools.performance_trend import get_performance_trend
from student_agent.tools.risk_assessment import get_risk_assessment
from student_agent.tools.student_courses import list_student_courses


def _guarded(config, user_course_id, tool_function, *extra):
    """Run a tool only for a student who is logged in AND owns the course."""
    student_id = get_student_id(config)
    if student_id is None:
        return {"status": "NOT_LOGGED_IN"}
    if not owns_course(student_id, user_course_id):
        return {"status": "NOT_YOURS"}
    return tool_function(user_course_id, *extra)


@tool("list_student_courses")
def list_courses_tool(config: RunnableConfig) -> dict:
    """List every course the logged-in student is enrolled in.

    Returns each course's name and its user_course_id. Call this first whenever
    the student mentions a course by name, because every other tool needs the
    user_course_id. Never guess an id. Completed courses are included
    (completed=true): assume the current ones unless the student asks about an
    old course.
    """
    student_id = get_student_id(config)
    if student_id is None:
        return {"status": "NOT_LOGGED_IN"}
    return list_student_courses(student_id)


@tool("get_course_overview")
def course_overview_tool(user_course_id: int, config: RunnableConfig) -> dict:
    """Official position of the student in one course.

    Returns the marks earned so far, the minimum mark still required in the
    final exam (required_in_final) and what percent of the final that is, which
    rule decides it (binding_rule: TOTAL or FINAL_MINIMUM), whether passing is
    still possible, and the days left to the final. required_in_final is a
    minimum requirement, NOT a prediction of what the student will score.
    Check 'status' first: INSUFFICIENT_DATA means the midterm mark is not
    recorded.
    """
    return _guarded(config, user_course_id, get_course_overview)


@tool("get_assessment_breakdown")
def assessment_breakdown_tool(user_course_id: int, config: RunnableConfig) -> dict:
    """Every quiz, assignment, oral, project and so on of the student in one course.

    For each one: score, percentage, weight, points lost and status (GRADED,
    GRADED_LATE, MISSING, PENDING). Also a summary by type and the type that
    lost the most points. Use it to answer where the student lost marks.
    """
    return _guarded(config, user_course_id, get_assessment_breakdown)


@tool("get_performance_trend")
def performance_trend_tool(user_course_id: int, config: RunnableConfig) -> dict:
    """Whether the student's graded results are going UP, DOWN or FLAT over time.

    Returns the series of percentages in date order, the average of the earlier
    results versus the recent ones, and the biggest drop between two
    consecutive assessments. Only graded work is used: missing work is ignored
    here (see get_missing_work).
    """
    return _guarded(config, user_course_id, get_performance_trend)


@tool("get_attendance_detail")
def attendance_detail_tool(user_course_id: int, config: RunnableConfig) -> dict:
    """Lecture attendance of the student in one course.

    Returns the attendance percentage, the lectures missed (with date and
    topic), the longest and the current streak of consecutive absences, and
    the attendance in the most recent lectures. A lecture with no recorded
    result counts as not_recorded, never as an absence.
    """
    return _guarded(config, user_course_id, get_attendance_detail)


@tool("get_missing_work")
def missing_work_tool(user_course_id: int, config: RunnableConfig) -> dict:
    """Work the student did not submit, submitted late, or still has coming up.

    Missing items include days overdue and points lost. Upcoming items include
    days left. Late items are listed as a fact only: they are not counted as
    lost points.
    """
    return _guarded(config, user_course_id, get_missing_work)


@tool("simulate_final_score")
def final_simulation_tool(
    user_course_id: int, hypothetical_final: float, config: RunnableConfig
) -> dict:
    """What-if: would the student pass with a made-up final exam mark?

    hypothetical_final is a mark out of the final's maximum, NOT a percentage:
    convert a percentage to marks before calling. Both rules are applied (total
    at least the pass mark AND final at least the minimum). outcome is
    PASS_GUARANTEED, FAIL_GUARANTEED, or DEPENDS (it depends on assessments
    still pending: needed_from_pending says how many points are needed from
    them). Never do this arithmetic yourself, always call this tool.
    """
    return _guarded(
        config, user_course_id, simulate_final_score, hypothetical_final
    )


@tool("get_risk_assessment")
def risk_assessment_tool(user_course_id: int, config: RunnableConfig) -> dict:
    """Overall risk level of failing one course, with the evidence behind it.

    risk_level is LOW, MEDIUM, HIGH, RANGE or UNKNOWN. Each evidence item has a
    code and the numbers behind it: every reason given to the student must come
    from this evidence. data_gaps lists what could not be seen (for example
    MIDTERM_NOT_RECORDED): always tell the student about them. If risk_level is
    RANGE, the level depends on the missing midterm mark: explain both cases
    using midterm_scenarios.
    """
    return _guarded(config, user_course_id, get_risk_assessment)


ALL_TOOLS = [
    list_courses_tool,
    course_overview_tool,
    assessment_breakdown_tool,
    performance_trend_tool,
    attendance_detail_tool,
    missing_work_tool,
    final_simulation_tool,
    risk_assessment_tool,
]