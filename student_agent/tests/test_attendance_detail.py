from datetime import date

from student_agent.tools.attendance_detail import (
    absence_streaks,
    build_attendance,
    count_attendance,
    list_absences,
    recent_attendance,
    select_counted_lectures,
)
TODAY = date(2026, 11, 1)


def lec(n, attended):
    return (f"Lecture {n}", date(2026, 10, n), f"Topic {n}", attended)


def ten_lectures(absent_numbers):
    return [lec(n, n not in absent_numbers) for n in range(1, 11)]


def test_future_lectures_are_skipped():
    rows = [lec(1, True), ("Lecture F", date(2026, 12, 1), "X", None)]
    counted = select_counted_lectures(rows, None, TODAY)
    assert [c["name"] for c in counted] == ["Lecture 1"]


def test_lectures_before_enrollment_are_skipped():
    rows = [lec(n, True) for n in range(1, 7)]
    counted = select_counted_lectures(rows, date(2026, 10, 5), TODAY)
    assert [c["name"] for c in counted] == ["Lecture 5", "Lecture 6"]


def test_sorted_by_date():
    rows = [lec(3, True), lec(1, True), lec(2, True)]
    counted = select_counted_lectures(rows, None, TODAY)
    assert [c["name"] for c in counted] == ["Lecture 1", "Lecture 2", "Lecture 3"]


def test_counts_and_percentage():
    counted = select_counted_lectures(ten_lectures([3, 7, 9]), None, TODAY)
    r = count_attendance(counted)
    assert r["attended"] == 7
    assert r["absent"] == 3
    assert r["attendance_pct"] == 70.0


def test_unrecorded_is_not_absent():
    rows = [lec(1, True), lec(2, None), lec(3, False)]
    r = count_attendance(select_counted_lectures(rows, None, TODAY))
    assert r["held"] == 3
    assert r["recorded"] == 2
    assert r["not_recorded"] == 1
    assert r["attended"] == 1
    assert r["absent"] == 1
    assert r["attendance_pct"] == 50.0


def test_nothing_recorded_gives_no_percentage():
    r = count_attendance(select_counted_lectures([lec(1, None)], None, TODAY))
    assert r["held"] == 1
    assert r["attendance_pct"] is None


def test_list_absences_ignores_unrecorded():
    rows = [lec(1, True), lec(2, False), lec(3, None)]
    absences = list_absences(select_counted_lectures(rows, None, TODAY))
    assert absences == [{"name": "Lecture 2", "date": "2026-10-02", "topic": "Topic 2"}]


def counted_of(rows):
    return select_counted_lectures(rows, None, TODAY)


def test_single_absences_give_streak_of_one():
    r = absence_streaks(counted_of(ten_lectures([3, 7, 9])))
    assert r["longest_absence_streak"] == 1
    assert r["longest_streak_from"] == "Lecture 3"
    assert r["current_absence_streak"] == 0


def test_longest_streak_in_the_middle():
    r = absence_streaks(counted_of(ten_lectures([2, 3, 4, 8])))
    assert r["longest_absence_streak"] == 3
    assert r["longest_streak_from"] == "Lecture 2"
    assert r["longest_streak_to"] == "Lecture 4"
    assert r["current_absence_streak"] == 0


def test_current_streak_at_the_end():
    r = absence_streaks(counted_of(ten_lectures([8, 9, 10])))
    assert r["current_absence_streak"] == 3
    assert r["longest_absence_streak"] == 3


def test_unrecorded_lecture_breaks_a_streak():
    rows = [lec(1, False), lec(2, False), lec(3, None), lec(4, False)]
    r = absence_streaks(counted_of(rows))
    assert r["longest_absence_streak"] == 2
    assert r["current_absence_streak"] == 1


def test_no_absences_at_all():
    r = absence_streaks(counted_of(ten_lectures([])))
    assert r["longest_absence_streak"] == 0
    assert r["longest_streak_from"] is None
    assert r["current_absence_streak"] == 0


def test_recent_uses_the_last_four():
    r = recent_attendance(counted_of(ten_lectures([1, 2, 3, 4, 5, 6])))
    assert r == {"lectures": 4, "attendance_pct": 100.0}


def test_recent_with_mixed_results():
    r = recent_attendance(counted_of(ten_lectures([8, 9])))
    assert r == {"lectures": 4, "attendance_pct": 50.0}


def test_recent_with_few_lectures():
    r = recent_attendance(counted_of([lec(1, True), lec(2, False)]))
    assert r == {"lectures": 2, "attendance_pct": 50.0}


def test_recent_ignores_unrecorded():
    r = recent_attendance(counted_of([lec(1, True), lec(2, None)]))
    assert r == {"lectures": 1, "attendance_pct": 100.0}


def test_build_full_result():
    r = build_attendance(ten_lectures([3, 7, 9]), None, TODAY)
    assert r["status"] == "OK"
    assert r["attended"] == 7
    assert r["absent"] == 3
    assert r["attendance_pct"] == 70.0
    assert len(r["absences"]) == 3
    assert r["longest_absence_streak"] == 1
    assert r["recent"] == {"lectures": 4, "attendance_pct": 50.0}


def test_build_with_no_lectures():
    assert build_attendance([], None, TODAY) == {"status": "NO_LECTURES_HELD"}


def test_build_with_nothing_recorded():
    r = build_attendance([lec(1, None)], None, TODAY)
    assert r["status"] == "NO_ATTENDANCE_RECORDED"
    assert r["attendance_pct"] is None    