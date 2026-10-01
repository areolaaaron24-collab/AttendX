import hashlib
import sqlite3

from database import get_connection


# ============================================================
# PASSWORD FUNCTIONS
# ============================================================

def hash_password(password):
    """
    Converts a password into a SHA-256 hash.
    The original password is never stored.
    """

    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


def verify_password(password, stored_hash):
    """
    Checks whether the entered password
    matches the stored password hash.
    """

    return hash_password(password) == stored_hash


# ============================================================
# STUDENT ACCOUNT FUNCTIONS
# ============================================================

def register_student(
    school_id,
    password,
    name,
    course,
    year,
    section
):
    """
    Creates a new student account.

    Returns:
        student_id if successful
        None if School ID already exists
    """

    connection = get_connection()

    cursor = connection.cursor()

    password_hash = hash_password(
        password
    )

    try:

        cursor.execute("""
            INSERT INTO students
            (
                school_id,
                password,
                name,
                course,
                year,
                section
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            school_id,
            password_hash,
            name,
            course,
            year,
            section
        ))

        connection.commit()

        student_id = cursor.lastrowid

        connection.close()

        return student_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def login_student(
    school_id,
    password
):
    """
    Logs in a student.

    Returns:
        Student database record if correct
        None if login fails
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            school_id,
            password,
            name,
            course,
            year,
            section
        FROM students
        WHERE school_id = ?
    """, (
        school_id,
    ))

    student = cursor.fetchone()

    connection.close()

    if student is None:
        return None

    stored_hash = student[2]

    if verify_password(
        password,
        stored_hash
    ):
        return student

    return None


def get_student_account(
    school_id
):
    """
    Gets a student account using School ID.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            school_id,
            password,
            name,
            course,
            year,
            section
        FROM students
        WHERE school_id = ?
    """, (
        school_id,
    ))

    student = cursor.fetchone()

    connection.close()

    return student


def change_student_password(
    school_id,
    new_password
):
    """
    Changes the student's password.
    """

    connection = get_connection()

    cursor = connection.cursor()

    new_hash = hash_password(
        new_password
    )

    cursor.execute("""
        UPDATE students
        SET password = ?
        WHERE school_id = ?
    """, (
        new_hash,
        school_id
    ))

    connection.commit()

    changed = cursor.rowcount > 0

    connection.close()

    return changed


# ============================================================
# TEACHER ACCOUNT FUNCTIONS
# ============================================================

def register_teacher(
    teacher_id,
    password,
    name
):
    """
    Creates a new teacher account.

    Returns:
        teacher database ID if successful
        None if Teacher ID already exists
    """

    connection = get_connection()

    cursor = connection.cursor()

    password_hash = hash_password(
        password
    )

    try:

        cursor.execute("""
            INSERT INTO teachers
            (
                teacher_id,
                password,
                name
            )
            VALUES (?, ?, ?)
        """, (
            teacher_id,
            password_hash,
            name
        ))

        connection.commit()

        teacher_database_id = (
            cursor.lastrowid
        )

        connection.close()

        return teacher_database_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def login_teacher(
    teacher_id,
    password
):
    """
    Logs in a teacher.

    Returns:
        Teacher database record if correct
        None if login fails
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            password,
            name
        FROM teachers
        WHERE teacher_id = ?
    """, (
        teacher_id,
    ))

    teacher = cursor.fetchone()

    connection.close()

    if teacher is None:
        return None

    stored_hash = teacher[2]

    if verify_password(
        password,
        stored_hash
    ):
        return teacher

    return None


def get_teacher_account(
    teacher_id
):
    """
    Gets a teacher account using Teacher ID.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            password,
            name
        FROM teachers
        WHERE teacher_id = ?
    """, (
        teacher_id,
    ))

    teacher = cursor.fetchone()

    connection.close()

    return teacher


def change_teacher_password(
    teacher_id,
    new_password
):
    """
    Changes the teacher's password.
    """

    connection = get_connection()

    cursor = connection.cursor()

    new_hash = hash_password(
        new_password
    )

    cursor.execute("""
        UPDATE teachers
        SET password = ?
        WHERE teacher_id = ?
    """, (
        new_hash,
        teacher_id
    ))

    connection.commit()

    changed = cursor.rowcount > 0

    connection.close()

    return changed


# ============================================================
# ACCOUNT EXISTENCE CHECKS
# ============================================================

def student_exists(
    school_id
):
    """
    Checks whether a student account exists.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM students
        WHERE school_id = ?
    """, (
        school_id,
    ))

    result = cursor.fetchone()

    connection.close()

    return result is not None


def teacher_exists(
    teacher_id
):
    """
    Checks whether a teacher account exists.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM teachers
        WHERE teacher_id = ?
    """, (
        teacher_id,
    ))

    result = cursor.fetchone()

    connection.close()

    return result is not None


# ============================================================
# PASSWORD VALIDATION
# ============================================================

def is_valid_password(
    password
):
    """
    Basic password validation.

    Minimum length:
    6 characters
    """

    if password is None:
        return False

    if len(password) < 6:
        return False

    return True


# ============================================================
# LOGIN INFORMATION
# ============================================================

def get_student_login_information(
    school_id,
    password
):
    """
    Returns basic student information
    after successful login.
    """

    student = login_student(
        school_id,
        password
    )

    if student is None:
        return None

    return {
        "id": student[0],
        "school_id": student[1],
        "name": student[3],
        "course": student[4],
        "year": student[5],
        "section": student[6]
    }


def get_teacher_login_information(
    teacher_id,
    password
):
    """
    Returns basic teacher information
    after successful login.
    """

    teacher = login_teacher(
        teacher_id,
        password
    )

    if teacher is None:
        return None

    return {
        "id": teacher[0],
        "teacher_id": teacher[1],
        "name": teacher[3]
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("ATTENDX Authentication Module")
    print("------------------------------")
    print("Authentication functions loaded.")
    print("Password hashing is enabled.")