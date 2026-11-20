# University rules. Written once here and used by every tool.

# Minimum mark a student must get in the final exam paper itself,
# even if the total mark is enough to pass.
from ast import If


FINAL_MIN = 20


# Trend analysis
# TREND_MIN_POINTS must be bigger than TREND_RECENT_COUNT,
# otherwise there is nothing left to compare the recent results with.
TREND_MIN_POINTS = 3      # fewest graded assessments needed to say anything
TREND_RECENT_COUNT = 2    # how many of the latest assessments count as "recent"
TREND_THRESHOLD = 10.0    # change (in percentage points) that counts as real movement

#If performance increases by 10 percentage points or more → UP.
# If it decreases by 10 percentage points or more → DOWN.
# If the change is less than 10 (whether an increase or a decrease) → FLAT.
# Note: These are percentage points, not a relative percentage increase.
#
# For example, moving from 60% to 70% = an increase of 10 percentage points.

# Attendance analysis
ATTENDANCE_RECENT_COUNT = 4   # how many of the latest recorded lectures count as "recent"


# Risk assessment (design choices of the team, to be calibrated on real data)
RISK_FINAL_PCT_MEDIUM = 60       # % of the final the student must score
RISK_FINAL_PCT_HIGH = 80
RISK_ATTENDANCE_MEDIUM = 75      # attendance % below this is a warning
RISK_ATTENDANCE_HIGH = 50
RISK_ABSENCE_STREAK = 3          # consecutive absences happening right now
RISK_MISSING_POINTS_MEDIUM = 10  # points lost on missing work
RISK_MISSING_POINTS_HIGH = 20
RISK_URGENT_DAYS = 14            # exam closer than this raises MEDIUM to HIGH

# University rule: attendance % under which a student may be barred from the exam.
# None means "rule not confirmed yet", so it is switched off.
ATTENDANCE_BAR_PCT = None

# Total marks of every course (coursework + final). Used only to catch bad course data.
COURSE_TOTAL = 100