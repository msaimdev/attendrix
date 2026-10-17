import threading

from app.attendance import AttendanceManager
from app.attendance_session import AttendanceSession
from app.email_service import EmailService
from app.calendar import CalendarService
from app.database import SessionLocal
from app.models import SchoolCalendar, SchoolSettings
from app.timezone import school_now, school_today
from app.config import settings


class AttendanceScheduler:
    """
    Automatically starts the school-wide attendance session
    when the configured attendance window is active.

    Responsibilities:
        - use the school's configured timezone
        - monitor the attendance time window
        - check school-wide calendar rules
        - ensure only ONE automatic session starts per day

    AttendanceSession remains responsible for:
        - face recognition
        - student attendance
        - student leave
        - class-specific calendar rules
        - duplicate attendance protection
    """

    def __init__(
        self,
        camera_index=0,
        check_interval_seconds=30,
    ):
        if check_interval_seconds < 1:
            raise ValueError(
                "check_interval_seconds must be at least 1."
            )

        self.camera_index = camera_index
        self.check_interval_seconds = check_interval_seconds

        self.running = False

        # Event used to interrupt the scheduler's
        # waiting period immediately during shutdown.
        self.stop_event = threading.Event()

        # Prevent multiple automatic sessions
        # during the same school day.
        self.last_started_date = None

        # Prevent multiple daily attendance reports
        # from being sent for the same school day.
        self.last_report_date = None

        self.calendar_service = CalendarService()

        # ----------------------------------------------------
        # LIVE ATTENDANCE SESSION
        # ----------------------------------------------------

        self.session_thread = None
        self.session = None

    # ========================================================
    # LOAD SETTINGS
    # ========================================================

    def get_settings(self):
        """Load the school's attendance settings."""

        db = SessionLocal()

        try:
            return (
                db.query(SchoolSettings)
                .order_by(SchoolSettings.id)
                .first()
            )
        finally:
            db.close()

    # ========================================================
    # SCHOOL CALENDAR
    # ========================================================

    def get_calendar_status(self, target_date):
        """
        Check ONLY school-wide calendar rules.

        Class-specific calendar rules are handled by
        AttendanceSession after a student is recognized.
        """

        db = SessionLocal()

        try:
            calendar_entry = (
                db.query(SchoolCalendar)
                .filter(
                    SchoolCalendar.start_date <= target_date,
                    SchoolCalendar.end_date >= target_date,
                )
                .order_by(SchoolCalendar.id.desc())
                .first()
            )

            if calendar_entry is None:
                return {
                    "allowed": True,
                    "reason": (
                        "school calendar has no OFF rule"
                    ),
                    "day_type": None,
                    "title": None,
                    "is_off": False,
                }

            day_type = (
                calendar_entry.day_type.value
                if hasattr(
                    calendar_entry.day_type,
                    "value",
                )
                else str(calendar_entry.day_type)
            )

            if calendar_entry.is_off:
                return {
                    "allowed": False,
                    "reason": (
                        "school calendar has an OFF rule"
                    ),
                    "day_type": day_type,
                    "title": calendar_entry.title,
                    "is_off": True,
                }

            return {
                "allowed": True,
                "reason": (
                    "school calendar explicitly "
                    "allows attendance"
                ),
                "day_type": day_type,
                "title": calendar_entry.title,
                "is_off": False,
            }

        finally:
            db.close()

    # ========================================================
    # TIME WINDOW
    # ========================================================

    def is_within_attendance_window(
        self,
        current_time,
        settings,
    ):
        """
        Return True when the school-local current time
        is inside the configured attendance window.
        """

        return (
            settings.attendance_start_time
            <= current_time
            <= settings.attendance_end_time
        )

    # ========================================================
    # DAILY SESSION GUARD
    # ========================================================

    def already_started_today(self, target_date):
        """
        Return True when today's automatic attendance
        session has already started.
        """

        return self.last_started_date == target_date

    # ========================================================
    # SESSION THREAD
    # ========================================================

    def _run_attendance_session(self, target_date):
        """
        Run the live attendance session independently from
        the scheduler monitoring thread.
        """

        try:
            self.session = AttendanceSession(
                camera_index=self.camera_index,
                target_date=target_date,
                preview_window=True,
            )

            self.session.start()
            self.send_daily_attendance_report(target_date)

        except Exception as error:
            print()
            print(
                "ERROR: Automatic attendance session "
                f"failed: {error}"
            )

        finally:
            self.session = None

            print()
            print(
                "Attendance session ended."
            )

            print(
                "Scheduler is monitoring again."
            )

            print()


    # ========================================================
    # DAILY ATTENDANCE REPORT
    # ========================================================

    def send_daily_attendance_report(self, target_date):
        """
        Generate and send the daily attendance report.

        Only one report may be sent for a given school day.
        """

        # ----------------------------------------------------
        # DAILY REPORT GUARD
        # ----------------------------------------------------

        if self.last_report_date == target_date:
            print(
                "Daily attendance report has already "
                "been sent for this date."
            )
            return False

        db = SessionLocal()

        try:
            school_settings = (
                db.query(SchoolSettings)
                .order_by(SchoolSettings.id)
                .first()
            )
        finally:
            db.close()

        # ----------------------------------------------------
        # REPORT EMAIL CONFIGURATION
        # ----------------------------------------------------

        if school_settings is None:
            print(
                "Daily attendance report was not sent: "
                "school settings are not configured."
            )
            return False

        if not school_settings.report_email:
            print(
                "Daily attendance report was not sent: "
                "no report email is configured."
            )
            return False

        # ----------------------------------------------------
        # GENERATE REPORT
        # ----------------------------------------------------

        try:
            attendance_manager = AttendanceManager()

            report = attendance_manager.generate_report(
                target_date
            )

            email_service = EmailService()

            body = (
                email_service.build_attendance_report_email(
                    report=report,
                    school_name=school_settings.school_name,
                )
            )

            subject = (
                f"{school_settings.school_name} "
                f"- Daily Attendance Report "
                f"- {target_date.isoformat()}"
            )

            result = email_service.send_email(
                recipient=school_settings.report_email,
                subject=subject,
                body=body,
            )

            if result["success"]:
                self.last_report_date = target_date

                print(
                    "Daily attendance report sent "
                    f"successfully to "
                    f"{school_settings.report_email}."
                )

                return True

            print(
                "Daily attendance report could not be sent."
            )

            return False

        except Exception as error:
            print()
            print(
                "ERROR: Daily attendance report "
                f"failed: {error}"
            )
            print()

            return False

    # ========================================================
    # START SESSION THREAD
    # ========================================================

    def start_attendance_session(self, target_date):
        """
        Start the live attendance session in its own thread.

        The scheduler thread remains free to monitor the
        application lifecycle and shutdown state.
        """

        if (
            self.session_thread is not None
            and self.session_thread.is_alive()
        ):
            print(
                "Attendance session is already running."
            )
            return False

        self.session_thread = threading.Thread(
            target=self._run_attendance_session,
            args=(target_date,),
            name="attendance-session",
            daemon=True,
        )

        self.session_thread.start()

        return True

    # ========================================================
    # STATUS
    # ========================================================

    def is_session_active(self):
        """
        Return True if a live attendance session is currently
        running (i.e. the camera is in active use for
        automatic attendance right now).

        Used to prevent other features (e.g. student
        registration) from opening a second capture on the
        same physical camera while attendance is in progress.
        """

        return (
            self.session_thread is not None
            and self.session_thread.is_alive()
        )

    def get_status(self):
        """
        Determine whether an automatic attendance session
        should currently start.
        """

        now = school_now()
        today = school_today()

        settings = self.get_settings()

        if settings is None:
            return {
                "should_start": False,
                "reason": (
                    "No school attendance settings "
                    "have been configured."
                ),
                "date": today,
                "time": now.time(),
                "calendar_allowed": False,
                "calendar_reason": None,
                "calendar_title": None,
                "calendar_day_type": None,
            }

        # ----------------------------------------------------
        # TIME WINDOW
        # ----------------------------------------------------

        if not self.is_within_attendance_window(
            current_time=now.time(),
            settings=settings,
        ):
            return {
                "should_start": False,
                "reason": (
                    "Current school-local time is "
                    "outside the attendance window."
                ),
                "date": today,
                "time": now.time(),
                "calendar_allowed": None,
                "calendar_reason": None,
                "calendar_title": None,
                "calendar_day_type": None,
            }

        # ----------------------------------------------------
        # SCHOOL CALENDAR
        # ----------------------------------------------------

        calendar_status = self.get_calendar_status(today)

        if not calendar_status["allowed"]:
            return {
                "should_start": False,
                "reason": (
                    "Attendance window is active, "
                    "but the school calendar marks "
                    "today as OFF."
                ),
                "date": today,
                "time": now.time(),
                "calendar_allowed": False,
                "calendar_reason": calendar_status["reason"],
                "calendar_title": calendar_status["title"],
                "calendar_day_type": calendar_status["day_type"],
            }

        # ----------------------------------------------------
        # DAILY GUARD
        # ----------------------------------------------------

        if self.already_started_today(today):
            return {
                "should_start": False,
                "reason": (
                    "Attendance session has already "
                    "started automatically today."
                ),
                "date": today,
                "time": now.time(),
                "calendar_allowed": True,
                "calendar_reason": calendar_status["reason"],
                "calendar_title": calendar_status["title"],
                "calendar_day_type": calendar_status["day_type"],
            }

        # ----------------------------------------------------
        # START CONDITIONS SATISFIED
        # ----------------------------------------------------

        return {
            "should_start": True,
            "reason": (
                "Attendance window is active and "
                "the school calendar allows attendance."
            ),
            "date": today,
            "time": now.time(),
            "calendar_allowed": True,
            "calendar_reason": calendar_status["reason"],
            "calendar_title": calendar_status["title"],
            "calendar_day_type": calendar_status["day_type"],
        }

    # ========================================================
    # RUN ONCE
    # ========================================================

    def run_once(self):
        """
        Check whether today's automatic attendance
        session should start.

        Returns:
            True  -> session start requested
            False -> nothing started
        """

        if self.stop_event.is_set():
            return False

        # Do not start another session while one is active.
        if (
            self.session_thread is not None
            and self.session_thread.is_alive()
        ):
            return False

        status = self.get_status()

        print()
        print("========================================")
        print("       AUTOMATIC ATTENDANCE CHECK")
        print("========================================")

        print(
            f"Date: {status['date'].isoformat()}"
        )

        print(
            "School Time: "
            f"{status['time'].strftime('%H:%M:%S')}"
        )

        print(
            "Attendance Scope: Entire School"
        )

        print()

        print(
            f"Decision: {status['reason']}"
        )

        if status.get("calendar_allowed") is not None:

            if status["calendar_allowed"]:
                print(
                    "Calendar: Normal school day"
                )

                if status.get("calendar_title"):
                    print(
                        f"Calendar Event: "
                        f"{status['calendar_title']}"
                    )

            else:
                print(
                    "Calendar: SCHOOL OFF"
                )

                if status.get("calendar_title"):
                    print(
                        f"Calendar Event: "
                        f"{status['calendar_title']}"
                    )

        print(
            "========================================"
        )
        print()

        if not status["should_start"]:
            return False

        if self.stop_event.is_set():
            return False

        print(
            "Attendance conditions are satisfied."
        )

        print(
            "Starting school-wide attendance session..."
        )

        print()

        # Mark the day before starting the live session.
        self.last_started_date = status["date"]

        started = self.start_attendance_session(
            target_date=status["date"]
        )

        if not started:
            self.last_started_date = None
            return False

        return True

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):
        """
        Request the scheduler to stop.

        Also request the active attendance session to stop.
        """

        self.running = False
        self.stop_event.set()

        if self.session is not None:
            try:
                self.session.stop()
            except Exception as error:
                print(
                    "Error while stopping attendance "
                    f"session: {error}"
                )

    # ========================================================
    # CONTINUOUS RUNNER
    # ========================================================

    def run_forever(self):
        """
        Continuously monitor the attendance window.

        Only one automatic attendance session may start
        per school day.
        """

        self.running = True
        self.stop_event.clear()

        print()
        print("========================================")
        print("     AUTOMATIC ATTENDANCE SCHEDULER")
        print("========================================")

        print(
            "Attendance Scope: Entire School"
        )

        print(
            "Check Interval: "
            f"{self.check_interval_seconds} seconds"
        )

        print(
            "Press Ctrl+C to stop scheduler."
        )

        print("========================================")
        print()

        try:
            while self.running and not self.stop_event.is_set():

                self.run_once()

                if self.stop_event.wait(
                    self.check_interval_seconds
                ):
                    break

        except KeyboardInterrupt:
            print()
            print(
                "Automatic attendance scheduler stopped."
            )

        finally:
            self.running = False
            self.stop_event.set()
