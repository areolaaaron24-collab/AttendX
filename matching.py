from database import (
    get_connection,
    get_student_by_id,
    get_schedule_by_id,
    student_is_enrolled
)


# ============================================================
# STUDENT AND SCHEDULE MATCHING
# ============================================================

def check_student_schedule_match(
    student_id,
    schedule_id
):
    """
    Checks if the student matches
    the course, year, and section
    of the selected schedule.
    """

    student = get_student_by_id(
        student_id
    )

    schedule = get_schedule_by_id(
        schedule_id
    )

    if student is None:
        return {
            "matched": False,
            "message": "Student not found."
        }

    if schedule is None:
        return {
            "matched": False,
            "message": "Schedule not found."
        }

    student_course = student[4]
    student_year = student[5]
    student_section = student[6]

    schedule_course = schedule[2]
    schedule_section = schedule[4]
    schedule_year = schedule[5]

    if student_course != schedule_course:
        return {
            "matched": False,
            "message": "Course does not match."
        }

    if student_year != schedule_year:
        return {
            "matched": False,
            "message": "Year level does not match."
        }

    if student_section != schedule_section:
        return {
            "matched": False,
            "message": "Section does not match."
        }

    return {
        "matched": True,
        "message": "Student matches the schedule."
    }


# ============================================================
# ENROLLMENT MATCHING
# ============================================================

def check_student_enrollment(
    student_id,
    schedule_id
):
    """
    Checks if the student is officially
    connected to the schedule.
    """

    enrolled = student_is_enrolled(
        student_id,
        schedule_id
    )

    if enrolled:
        return {
            "matched": True,
            "message": "Student is enrolled in this class."
        }

    return {
        "matched": False,
        "message": "Student is not enrolled in this class."
    }


# ============================================================
# COMPLETE ATTENDANCE VALIDATION
# ============================================================

def validate_student_attendance(
    student_id,
    schedule_id
):
    """
    Complete validation before allowing
    a student to attend.

    Checks:
    1. Student exists
    2. Schedule exists
    3. Course matches
    4. Year matches
    5. Section matches
    6. Student is enrolled
    """

    schedule_match = check_student_schedule_match(
        student_id,
        schedule_id
    )

    if not schedule_match["matched"]:
        return schedule_match

    enrollment_match = check_student_enrollment(
        student_id,
        schedule_id
    )

    if not enrollment_match["matched"]:
        return enrollment_match

    return {
        "matched": True,
        "message": "Student is allowed to attend this class."
    }


# ============================================================
# GET STUDENTS FOR A SCHEDULE
# ============================================================

def get_schedule_students(
    schedule_id
):
    """
    Returns all students enrolled
    in a specific schedule.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            students.id,
            students.school_id,
            students.name,
            students.course,
            students.year,
            students.section

        FROM student_classes

        INNER JOIN students
            ON student_classes.student_id = students.id

        WHERE student_classes.schedule_id = ?

        ORDER BY students.name
    """, (
        schedule_id,
    ))

    students = cursor.fetchall()

    connection.close()

    return students


# ============================================================
# GET STUDENT'S MATCHING SCHEDULES
# ============================================================

def get_student_matching_schedules(
    student_id
):
    """
    Gets all schedules where the student's
    course, year, and section match.
    """

    student = get_student_by_id(
        student_id
    )

    if student is None:
        return []

    student_course = student[4]
    student_year = student[5]
    student_section = student[6]

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            course,
            subject,
            section,
            year,
            day,
            start_time,
            end_time

        FROM schedules

        WHERE course = ?
          AND year = ?
          AND section = ?

        ORDER BY
            day,
            start_time
    """, (
        student_course,
        student_year,
        student_section
    ))

    schedules = cursor.fetchall()

    connection.close()

    return schedules


# ============================================================
# GET COMPLETE CLASS INFORMATION
# ============================================================

def get_complete_schedule_information(
    schedule_id
):
    """
    Returns schedule information together
    with teacher information.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            schedules.id,
            schedules.course,
            schedules.subject,
            schedules.year,
            schedules.section,
            schedules.day,
            schedules.start_time,
            schedules.end_time,

            teachers.id,
            teachers.teacher_id,
            teachers.name

        FROM schedules

        INNER JOIN teachers
            ON schedules.teacher_id = teachers.id

        WHERE schedules.id = ?
    """, (
        schedule_id,
    ))

    information = cursor.fetchone()

    connection.close()

    return information


# ============================================================
# CHECK TEACHER OWNERSHIP
# ============================================================

def teacher_owns_schedule(
    teacher_id,
    schedule_id
):
    """
    Checks whether the selected schedule
    belongs to the teacher.
    """

    schedule = get_schedule_by_id(
        schedule_id
    )

    if schedule is None:
        return False

    schedule_teacher_id = schedule[1]

    return schedule_teacher_id == teacher_id


# ============================================================
# COMPLETE QR ATTENDANCE MATCH
# ============================================================

def validate_qr_attendance(
    student_id,
    schedule_id,
    teacher_id
):
    """
    Complete validation for QR attendance.

    Checks:
    1. Teacher owns the schedule
    2. Student matches schedule
    3. Student is enrolled
    """

    if not teacher_owns_schedule(
        teacher_id,
        schedule_id
    ):
        return {
            "matched": False,
            "message": "This schedule does not belong to the teacher."
        }

    attendance_check = validate_student_attendance(
        student_id,
        schedule_id
    )

    if not attendance_check["matched"]:
        return attendance_check

    return {
        "matched": True,
        "message": "QR attendance validation successful."
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("ATTENDX Matching Module")
    print("-----------------------")
    print("Student and schedule matching loaded.")
    print("Teacher ownership validation loaded.")
    print("Attendance validation loaded.")