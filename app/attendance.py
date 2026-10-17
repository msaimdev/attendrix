from datetime import datetime, timedelta
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    AttendanceStatus,
    SchoolSettings,
    Student,
    StudentAttendance,
    StudentLeave,
)
from app.timezone import school_now, school_today
from app.calendar import CalendarService


class AttendanceManager:
    """
    SQLite-backed attendance manager.

    Handles:
    - marking students present
    - preventing duplicate attendance
    - checking student leave
    - loading daily attendance
    - generating attendance reports
    - using the configured school timezone
    """

    calendar_service = CalendarService()

    # ============================================================
    # CHECK STUDENT LEAVE
    # ============================================================

    def get_student_leave(
        self,
        student_id,
        target_date=None,
    ):
        """
        Return the leave record covering the specified date.

        A student is considered on leave when:

            start_date <= target_date <= end_date

        If no target date is supplied, the current date in
        the configured school timezone is used.

        Returns:
            StudentLeave object if leave exists.
            None otherwise.
        """

        if target_date is None:
            target_date = school_today()

        db = SessionLocal()

        try:
            leave = db.scalar(
                select(StudentLeave)
                .where(
                    StudentLeave.student_id == student_id,
                    StudentLeave.start_date <= target_date,
                    StudentLeave.end_date >= target_date,
                )
                .order_by(
                    StudentLeave.start_date.desc()
                )
            )

            return leave

        finally:
            db.close()

    def is_student_on_leave(
        self,
        student_id,
        target_date=None,
    ):
        """
        Return True when the student is on approved leave
        for the specified date.
        """

        return (
            self.get_student_leave(
                student_id=student_id,
                target_date=target_date,
            )
            is not None
        )

    # ============================================================
    # MARK PRESENT
    # ============================================================

    def mark_present(
        self,
        student_id,
        student_name,
        student_class,
        attendance_date=None,
    ):
        """
        Mark a student present.

        Rules:

        1. Student must exist and be active.
        2. Student cannot be on leave.
        3. Student can only have one attendance record per day.
        4. Attendance date/time use the configured school timezone.

        attendance_date:
            Optional date used by AttendanceSession.

            If omitted, today's date in the configured school
            timezone is used.
        """

        # --------------------------------------------------------
        # Get one consistent school-local timestamp.
        #
        # This prevents date/time being calculated from different
        # moments around midnight.
        # --------------------------------------------------------

        now = school_now()

        if attendance_date is None:
            attendance_date = now.date()

        attendance_time = now.time()

        db = SessionLocal()

        try:
            # ----------------------------------------------------
            # Make sure student exists and is active
            # ----------------------------------------------------

            student = db.scalar(
                select(Student).where(
                    Student.id == student_id,
                    Student.is_active.is_(True),
                )
            )

            if student is None:
                return {
                    "success": False,
                    "already_marked": False,
                    "on_leave": False,
                    "error": "Student not found.",
                }

            # ----------------------------------------------------
            # Check student leave
            # ----------------------------------------------------

            leave = db.scalar(
                select(StudentLeave)
                .where(
                    StudentLeave.student_id == student_id,
                    StudentLeave.start_date <= attendance_date,
                    StudentLeave.end_date >= attendance_date,
                )
                .order_by(
                    StudentLeave.start_date.desc()
                )
            )

            if leave is not None:
                return {
                    "success": False,
                    "already_marked": False,
                    "on_leave": True,
                    "record": {
                        "student_id": student.id,
                        "student_name": student.name,
                        "class": student.student_class,
                        "date": attendance_date.isoformat(),
                        "status": "ON_LEAVE",
                        "leave_reason": leave.reason,
                    },
                }

            # ----------------------------------------------------
            # Check for existing attendance
            # ----------------------------------------------------

            existing = db.scalar(
                select(StudentAttendance).where(
                    StudentAttendance.student_id == student_id,
                    StudentAttendance.date == attendance_date,
                )
            )

            if existing is not None:
                return {
                    "success": False,
                    "already_marked": True,
                    "on_leave": False,
                    "record": self._record_to_dict(
                        existing,
                        student.name,
                        student.student_class,
                    ),
                }

            # ----------------------------------------------------
            # DETERMINE ATTENDANCE STATUS
            # ----------------------------------------------------

            school_settings = db.scalar(
                select(SchoolSettings)
                .order_by(SchoolSettings.id)
            )

            attendance_status = (
                AttendanceStatus.PRESENT
            )

            if school_settings is not None:

                late_threshold = (
                    datetime.combine(
                        attendance_date,
                        school_settings.attendance_start_time,
                    )
                    + timedelta(
                        minutes=school_settings.late_after_minutes
                    )
                )

                current_attendance_datetime = (
                    datetime.combine(
                        attendance_date,
                        attendance_time,
                    )
                )

                if (
                    current_attendance_datetime
                    >= late_threshold
                ):
                    attendance_status = (
                        AttendanceStatus.LATE
                    )

            # ----------------------------------------------------
            # Create attendance record
            # ----------------------------------------------------

            attendance = StudentAttendance(
                student_id=student_id,
                date=attendance_date,
                time=attendance_time,
                status=attendance_status,
            )

            db.add(attendance)
            db.commit()
            db.refresh(attendance)

            return {
                "success": True,
                "already_marked": False,
                "on_leave": False,
                "record": self._record_to_dict(
                    attendance,
                    student.name,
                    student.student_class,
                ),
            }

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    # ============================================================
    # CHECK ATTENDANCE
    # ============================================================

    def is_marked_present(
        self,
        student_id,
        date=None,
    ):
        """
        Check whether a student is already marked present
        for the specified date.

        If no date is supplied, the current date in the
        configured school timezone is used.
        """

        if date is None:
            date = school_today()

        db = SessionLocal()

        try:
            existing = db.scalar(
                select(StudentAttendance).where(
                    StudentAttendance.student_id == student_id,
                    StudentAttendance.date == date,
                )
            )

            return existing is not None

        finally:
            db.close()


    def delete_attendance_record(self, attendance_id):
        """
        Delete one attendance record by database ID.

        Returns:
            True when a record was deleted.
            False when the record does not exist.
        """

        db = SessionLocal()

        try:
            record = db.get(
                StudentAttendance,
                attendance_id,
            )

            if record is None:
                return False

            db.delete(record)
            db.commit()

            return True

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    # ============================================================
    # LOAD DAILY ATTENDANCE
    # ============================================================

    def load_daily_attendance(
        self,
        date=None,
    ):
        """
        Load attendance records for a specific date.
        """

        if date is None:
            date = school_today()

        db = SessionLocal()

        try:
            records = db.scalars(
                select(StudentAttendance)
                .where(
                    StudentAttendance.date == date
                )
                .order_by(StudentAttendance.time)
            ).all()

            result = []

            for record in records:
                student = db.scalar(
                    select(Student).where(
                        Student.id == record.student_id
                    )
                )

                if student is None:
                    continue

                result.append(
                    self._record_to_dict(
                        record,
                        student.name,
                        student.student_class,
                    )
                )

            return result

        finally:
            db.close()

    # ============================================================
    # REPORT
    # ============================================================

    def generate_report(
        self,
        date=None,
    ):
        """
        Generate an attendance summary for a specific date.

        Expected-attendance rules:

        1. School-wide OFF:
           No student is expected to attend.

        2. Class-specific OFF:
           Students belonging to that class are not expected
           to attend.

        3. Student-specific approved leave:
           The student is not expected to attend and is reported
           separately as on_leave.

        4. Normal attendance day:
           Students without attendance are absent.

        Precedence:

            Calendar OFF
                ↓
            NOT EXPECTED

            Otherwise approved student leave
                ↓
            ON LEAVE

            Otherwise attendance exists
                ↓
            PRESENT

            Otherwise
                ↓
            ABSENT

        Attendance percentage is calculated only against
        students who were actually expected to attend.
        """

        if date is None:
            date = school_today()

        db = SessionLocal()

        try:
            # ----------------------------------------------------
            # LOAD ACTIVE STUDENTS
            # ----------------------------------------------------

            students = db.scalars(
                select(Student).where(
                    Student.is_active.is_(True)
                )
            ).all()

            # ----------------------------------------------------
            # LOAD ATTENDANCE
            # ----------------------------------------------------

            attendance_records = db.scalars(
                select(StudentAttendance).where(
                    StudentAttendance.date == date
                )
            ).all()

            # ----------------------------------------------------
            # LOAD STUDENT LEAVE
            # ----------------------------------------------------

            leave_records = db.scalars(
                select(StudentLeave).where(
                    StudentLeave.start_date <= date,
                    StudentLeave.end_date >= date,
                )
            ).all()

            leave_student_ids = {
                leave.student_id
                for leave in leave_records
            }

            # ----------------------------------------------------
            # ATTENDANCE IDS
            # ----------------------------------------------------

            present_student_ids = {
                record.student_id
                for record in attendance_records
            }

            # ----------------------------------------------------
            # RESOLVE CALENDAR RULES BY CLASS
            #
            # We resolve once per class instead of once per
            # student because all students in the same class
            # share the same calendar rule.
            # ----------------------------------------------------

            class_rules = {}

            for student in students:
                student_class = student.student_class

                if student_class not in class_rules:
                    class_rules[student_class] = (
                        self.calendar_service.get_attendance_rule(
                            db=db,
                            class_name=student_class,
                            target_date=date,
                        )
                    )

            # ----------------------------------------------------
            # DETERMINE EXPECTED STUDENTS
            # ----------------------------------------------------

            expected_students = []

            not_expected_students = []

            for student in students:

                rule = class_rules[
                    student.student_class
                ]

                # ------------------------------------------------
                # Calendar OFF takes priority over everything.
                #
                # This means a student whose class is OFF is
                # NOT EXPECTED, even if they also have a leave
                # record.
                # ------------------------------------------------

                if not rule["allowed"]:
                    not_expected_students.append(
                        student
                    )
                    continue

                # ------------------------------------------------
                # Approved individual leave removes the student
                # from expected attendance.
                # ------------------------------------------------

                if student.id in leave_student_ids:
                    continue

                expected_students.append(student)

            # ----------------------------------------------------
            # COUNTS
            # ----------------------------------------------------

            total_students = len(students)

            expected_student_count = len(
                expected_students
            )

            not_expected_count = len(
                not_expected_students
            )

            # ----------------------------------------------------
            # EFFECTIVE LEAVE
            #
            # A leave record only counts as ON LEAVE when the
            # student would otherwise be expected to attend.
            #
            # If their school/class is OFF, the calendar rule
            # takes precedence and they remain NOT EXPECTED.
            # ----------------------------------------------------

            effective_leave_student_ids = {
                student.id
                for student in students
                if (
                    student.id in leave_student_ids
                    and class_rules[
                        student.student_class
                    ]["allowed"]
                )
            }

            leave_students = len(
                effective_leave_student_ids
            )

            expected_student_ids = {
                student.id
                for student in expected_students
            }

            # ----------------------------------------------------
            # PRESENT
            # ----------------------------------------------------

            present_students = len(
                present_student_ids.intersection(
                    expected_student_ids
                )
            )

            # ----------------------------------------------------
            # ABSENT
            # ----------------------------------------------------

            absent_students = max(
                expected_student_count
                - present_students,
                0,
            )

            # ----------------------------------------------------
            # ATTENDANCE PERCENTAGE
            # ----------------------------------------------------

            attendance_percentage = (
                (
                    present_students
                    / expected_student_count
                )
                * 100
                if expected_student_count > 0
                else 0
            )

            # ----------------------------------------------------
            # CLASS SUMMARY
            # ----------------------------------------------------

            class_summary = {}

            for student in students:

                student_class = student.student_class

                if student_class not in class_summary:
                    class_summary[student_class] = {
                        "total_students": 0,
                        "expected_students": 0,
                        "present": 0,
                        "absent": 0,
                        "on_leave": 0,
                        "not_expected": 0,
                    }

                summary = class_summary[
                    student_class
                ]

                summary["total_students"] += 1

                rule = class_rules[
                    student_class
                ]

                # ------------------------------------------------
                # SCHOOL / CLASS OFF
                # ------------------------------------------------

                if not rule["allowed"]:
                    summary["not_expected"] += 1
                    continue

                # ------------------------------------------------
                # STUDENT LEAVE
                # ------------------------------------------------

                if (
                    student.id
                    in effective_leave_student_ids
                ):
                    summary["on_leave"] += 1
                    continue

                # ------------------------------------------------
                # EXPECTED STUDENT
                # ------------------------------------------------

                summary["expected_students"] += 1

                if student.id in present_student_ids:
                    summary["present"] += 1
                else:
                    summary["absent"] += 1

            # ----------------------------------------------------
            # RETURN REPORT
            # ----------------------------------------------------

            return {
                "date": date.isoformat(),

                "total_students": total_students,

                "expected_students": (
                    expected_student_count
                ),

                "present": present_students,

                "absent": absent_students,

                "on_leave": leave_students,

                "not_expected": not_expected_count,

                "attendance_percentage": round(
                    attendance_percentage,
                    2,
                ),

                "classes": class_summary,
            }

        finally:
            db.close()

    # ============================================================
    # INTERNAL CONVERTER
    # ============================================================

    @staticmethod
    def _record_to_dict(
        record,
        student_name,
        student_class,
    ):
        """
        Convert a StudentAttendance SQLAlchemy object
        into the dictionary format used by the application.
        """

        return {
            "id": record.id,
            "student_id": record.student_id,
            "student_name": student_name,
            "class": student_class,
            "date": record.date.isoformat(),
            "time": (
                record.time.strftime("%H:%M:%S")
                if record.time is not None
                else None
            ),
            "status": (
                record.status.value
                if hasattr(record.status, "value")
                else str(record.status)
            ),
        }