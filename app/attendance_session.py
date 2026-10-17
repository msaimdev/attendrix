import time
from collections import deque
from datetime import date

from app.timezone import school_now, school_today

import cv2

from app.attendance import AttendanceManager
from app.camera import CameraManager
from app.calendar import CalendarService
from app.database import SessionLocal
from app.models import SchoolSettings

from app.camera_stream import ThreadedVideoCapture


class AttendanceSession:
    """
    Manage one school-wide live attendance session.

    The session is NOT tied to an individual class.

    Flow:

        School Calendar Check
            ↓
        Camera Start
            ↓
        Detect
            ↓
        Recognize Student
            ↓
        Read Student's Class
            ↓
        Check Class Calendar
            ↓
        Confirm using 3 accepted matches
        within the latest 5 frames
            ↓
        Check Student Leave
            ↓
        Mark Attendance
            ↓
        Lock Student until departure
            ↓
        Ready for next student


    Attendance safety rules:

    1. Attendance is blocked when the entire school is OFF.

    2. One session handles students from ALL classes.

    3. A student's own class calendar is checked after
       that student is recognized.

    4. If the student's class is OFF, that student is
       not marked present.

    5. Unknown/rejected students never reach attendance.

    6. A student on leave cannot be marked PRESENT.

    7. One student can only be marked once per attendance date.

    8. target_date controls both:
           - calendar checking
           - attendance date

       This makes testing future dates safe.
    """

    def __init__(
        self,
        camera_index=0,
        target_date=None,
        confirmation_frames=5,
        required_matches=3,
        preview_window=False,
        departure_frames=10,
    ):
        self.camera_index = camera_index
        self.preview_window = preview_window

        # ====================================================
        # ATTENDANCE DATE
        # ====================================================

        if target_date is not None:
            if not isinstance(target_date, date):
                raise ValueError(
                    "target_date must be a datetime.date instance."
                )

        self.target_date = target_date

        # ====================================================
        # RECOGNITION CONFIGURATION
        # ====================================================

        if confirmation_frames < 1:
            raise ValueError(
                "confirmation_frames must be at least 1."
            )

        if required_matches < 1:
            raise ValueError(
                "required_matches must be at least 1."
            )

        if required_matches > confirmation_frames:
            raise ValueError(
                "required_matches cannot be greater "
                "than confirmation_frames."
            )

        if departure_frames < 1:
            raise ValueError(
                "departure_frames must be at least 1."
            )

        # ====================================================
        # MANAGERS / SERVICES
        # ====================================================

        self.camera_manager = CameraManager()
        self.attendance_manager = AttendanceManager()
        self.calendar_service = CalendarService()

        self.confirmation_frames = confirmation_frames
        self.required_matches = required_matches
        self.departure_frames = departure_frames

        self.camera = None

    # ========================================================
    # EFFECTIVE ATTENDANCE DATE
    # ========================================================

    def get_attendance_date(self):
        """
        Return the date used by this attendance session.

        If target_date was supplied, use it.

        Otherwise use today's local system date.
        """

        if self.target_date is not None:
            return self.target_date

        return school_today()

    # ========================================================
    # SCHOOL-WIDE CALENDAR CHECK
    # ========================================================

    def check_attendance_allowed(self):
        """
        Check whether attendance is allowed for the entire
        school on the session date.

        Class-specific rules are NOT checked here.

        They are checked individually after a student
        is recognized.
        """

        attendance_date = self.get_attendance_date()

        db = SessionLocal()

        try:

            school_rule = (
                self.calendar_service.get_school_calendar_day(
                    db=db,
                    target_date=attendance_date,
                )
            )

            if school_rule is None:

                return {
                    "allowed": True,
                    "source": "default",
                    "day_type": None,
                    "title": None,
                    "is_off": False,
                }

            return {
                "allowed": not school_rule.is_off,
                "source": "school",
                "day_type": school_rule.day_type.value,
                "title": school_rule.title,
                "is_off": school_rule.is_off,
            }

        finally:
            db.close()

    # ========================================================
    # STUDENT CLASS CALENDAR CHECK
    # ========================================================

    def check_student_class_attendance_allowed(
        self,
        student_class,
    ):
        """
        Check whether the recognized student's class is
        allowed to have attendance on the session date.

        School-wide rules automatically take priority inside
        CalendarService.get_attendance_rule().
        """

        if student_class is None:
            return {
                "allowed": False,
                "source": "invalid",
                "day_type": None,
                "title": None,
                "is_off": True,
            }

        class_name = str(student_class).strip()

        if not class_name:
            return {
                "allowed": False,
                "source": "invalid",
                "day_type": None,
                "title": None,
                "is_off": True,
            }

        attendance_date = self.get_attendance_date()

        db = SessionLocal()

        try:

            return self.calendar_service.get_attendance_rule(
                db=db,
                class_name=class_name,
                target_date=attendance_date,
            )

        finally:
            db.close()

    # ========================================================
    # CALENDAR STATUS
    # ========================================================

    def print_calendar_status(self, rule):
        """
        Print the school-wide attendance-calendar status.
        """

        attendance_date = self.get_attendance_date()

        print()
        print("========================================")
        print("       ATTENDANCE CALENDAR CHECK")
        print("========================================")

        print(
            f"Date: {attendance_date.isoformat()}"
        )

        print()

        if rule["allowed"]:

            print("Attendance: ALLOWED")

            if rule["source"] == "default":

                print(
                    "Calendar: Normal school day"
                )

            else:

                print(
                    f"Calendar: {rule['day_type']}"
                )

                print(
                    f"Title: {rule['title']}"
                )

        else:

            print("Attendance: BLOCKED")

            print(
                f"Reason: {rule['day_type']}"
            )

            print(
                f"Title: {rule['title']}"
            )

        print("========================================")
        print()

    # ========================================================
    # STUDENT CLASS CALENDAR BLOCK
    # ========================================================

    def print_class_calendar_block(
        self,
        student_name,
        student_class,
        rule,
    ):
        """
        Print a clear message when a student's class is OFF.
        """

        print()
        print(
            "ATTENDANCE BLOCKED: CLASS IS OFF"
        )

        print(
            f"Student: {student_name}"
        )

        print(
            f"Class: {student_class}"
        )

        print(
            f"Date: {self.get_attendance_date()}"
        )

        if rule.get("day_type"):
            print(
                f"Reason: {rule['day_type']}"
            )

        if rule.get("title"):
            print(
                f"Title: {rule['title']}"
            )

        print()

    # ========================================================
    # STUDENT LEAVE STATUS
    # ========================================================

    def print_leave_block(
        self,
        attendance_result,
    ):
        """
        Print a clear message when attendance is blocked
        because the recognized student is on leave.
        """

        record = attendance_result.get(
            "record",
            {},
        )

        print()
        print(
            "ATTENDANCE BLOCKED: STUDENT ON LEAVE"
        )

        print(
            f"Student: "
            f"{record.get('student_name')}"
        )

        print(
            f"Class: "
            f"{record.get('class')}"
        )

        print(
            f"Date: "
            f"{record.get('date')}"
        )

        reason = record.get(
            "leave_reason"
        )

        if reason:
            print(
                f"Reason: {reason}"
            )
        else:
            print(
                "Reason: No reason provided"
            )

        print()

    # ========================================================
    # START SESSION
    # ========================================================

    def start(self):
        """
        Start the school-wide live attendance session.

        School-wide calendar rules are checked BEFORE
        the camera is opened.

        Class-specific calendar rules are checked after
        each student is recognized.
        """

        # ====================================================
        # SCHOOL-WIDE CALENDAR GATE
        # ====================================================

        calendar_rule = (
            self.check_attendance_allowed()
        )

        self.print_calendar_status(
            calendar_rule
        )

        if not calendar_rule["allowed"]:

            print(
                "Attendance session will NOT start "
                "because attendance is OFF for this date."
            )

            return

        # ====================================================
        # CAMERA START
        # ====================================================

        self.camera = ThreadedVideoCapture(self.camera_index)

        if not self.camera.isOpened():

            print(
                "ERROR: Could not open camera."
            )

            return

        print("========================================")
        print("       FACE ATTENDANCE SESSION")
        print("========================================")

        print(
            "Attendance Scope: Entire School"
        )

        print(
            f"Attendance Date: "
            f"{self.get_attendance_date().isoformat()}"
        )

        print()
        print("Look at the camera.")
        print("Press Q to quit.")
        print()

        # ====================================================
        # CONFIRMATION STATE
        # ====================================================

        confirmation_window = deque(
            maxlen=self.confirmation_frames
        )

        confirmed_student_id = None
        departure_count = 0

        try:

            while True:

                # =============================================
                # ATTENDANCE WINDOW END CHECK
                # =============================================

                current_time = school_now().time()

                db = SessionLocal()

                try:
                    settings = (
                        db.query(SchoolSettings)
                        .order_by(SchoolSettings.id)
                        .first()
                    )
                finally:
                    db.close()

                if (
                    settings is not None
                    and current_time
                    > settings.attendance_end_time
                ):
                    print()
                    print(
                        "Attendance window has ended."
                    )
                    print(
                        "Ending automatic attendance session."
                    )
                    print()

                    break

                success, frame = (
                    self.camera.read()
                )

                if not success:

                    print(
                        "ERROR: Could not read camera frame."
                    )

                    break

                results = (
                    self.camera_manager.recognize_face(
                        frame
                    )
                )

                # =================================================
                # FACE RECOGNITION RESULT
                # =================================================

                if results:

                    result = max(
                        results,
                        key=lambda item: item["score"],
                    )

                    student_id = (
                        result["student_id"]
                    )

                    # ---------------------------------------------
                    # STUDENT ALREADY CONFIRMED
                    # ---------------------------------------------

                    if (
                        confirmed_student_id
                        == student_id
                    ):

                        departure_count = 0

                    else:

                        departure_count = 0

                        confirmation_window.append(
                            student_id
                        )

                        match_count = (
                            confirmation_window.count(
                                student_id
                            )
                        )

                        print(
                            f"\rConfirming "
                            f"{result['name']}: "
                            f"{match_count}/"
                            f"{self.required_matches} "
                            f"within "
                            f"{len(confirmation_window)}/"
                            f"{self.confirmation_frames} "
                            f"frames",
                            end="",
                            flush=True,
                        )

                        # =========================================
                        # CONFIRM STUDENT
                        # =========================================

                        if (
                            match_count
                            >= self.required_matches
                            and confirmed_student_id
                            != student_id
                        ):

                            confirmed_student_id = (
                                student_id
                            )

                            confirmation_window.clear()

                            print()
                            print()

                            print(
                                "================================"
                            )

                            print(
                                "STUDENT RECOGNIZED"
                            )

                            print(
                                f"Student ID: "
                                f"{result['student_id']}"
                            )

                            print(
                                f"Name: "
                                f"{result['name']}"
                            )

                            print(
                                f"Class: "
                                f"{result['class']}"
                            )

                            print(
                                f"Similarity: "
                                f"{result['score']:.3f}"
                            )

                            # =====================================
                            # CLASS CALENDAR CHECK
                            # =====================================

                            class_rule = (
                                self.check_student_class_attendance_allowed(
                                    result["class"]
                                )
                            )

                            if not class_rule["allowed"]:

                                self.print_class_calendar_block(
                                    student_name=result["name"],
                                    student_class=result["class"],
                                    rule=class_rule,
                                )

                                print(
                                    "Attendance was not marked "
                                    "because this student's "
                                    "class is OFF."
                                )

                                print(
                                    "================================"
                                )

                                print()

                                continue

                            # =====================================
                            # MARK ATTENDANCE
                            # =====================================

                            attendance_result = (
                                self.attendance_manager.mark_present(
                                    result["student_id"],
                                    result["name"],
                                    result["class"],
                                    attendance_date=(
                                        self.get_attendance_date()
                                    ),
                                )
                            )

                            # =====================================
                            # STUDENT ON LEAVE
                            # =====================================

                            if attendance_result.get(
                                "on_leave"
                            ):

                                self.print_leave_block(
                                    attendance_result
                                )

                            # =====================================
                            # ALREADY MARKED
                            # =====================================

                            elif attendance_result.get(
                                "already_marked"
                            ):

                                print(
                                    "Attendance: "
                                    "ALREADY MARKED"
                                )

                                print(
                                    "Existing record:",
                                    attendance_result.get(
                                        "record"
                                    ),
                                )

                            # =====================================
                            # SUCCESS
                            # =====================================

                            elif attendance_result.get(
                                "success"
                            ):

                                print(
                                    "Attendance: "
                                    "MARKED PRESENT"
                                )

                                print(
                                    "Record:",
                                    attendance_result.get(
                                        "record"
                                    ),
                                )

                            # =====================================
                            # OTHER FAILURE
                            # =====================================

                            else:

                                print(
                                    "Attendance: "
                                    "NOT MARKED"
                                )

                                print(
                                    "Result:",
                                    attendance_result,
                                )

                            print(
                                "================================"
                            )

                            print()

                # =================================================
                # NO ACCEPTED RECOGNITION
                # =================================================

                else:

                    confirmation_window.append(
                        None
                    )

                    if (
                        confirmed_student_id
                        is not None
                    ):

                        departure_count += 1

                        if (
                            departure_count
                            >= self.departure_frames
                        ):

                            print(
                                "Student left. "
                                "Ready for next student."
                            )

                            print()

                            confirmed_student_id = (
                                None
                            )

                            departure_count = 0

                            confirmation_window.clear()

                # =================================================
                # DISPLAY CAMERA
                # =================================================

                if self.preview_window:
                    cv2.imshow(
                        "Face Attendance - Live Session",
                        frame,
                    )

                    if (
                        cv2.waitKey(1) & 0xFF
                        == ord("q")
                    ):

                        break

                time.sleep(0.01)

        finally:

            self.stop()

    # ========================================================
    # STOP SESSION
    # ========================================================

    def stop(self):
        """
        Stop the attendance session.
        """

        if self.camera is not None:

            self.camera.release()

            self.camera = None

        if self.preview_window:
            cv2.destroyAllWindows()

        print()
        print("Camera stopped.")
