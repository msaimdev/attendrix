from contextlib import asynccontextmanager
from datetime import date, datetime
from threading import Thread
import time

import uvicorn
from fastapi import FastAPI, Depends, Request, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.attendance import AttendanceManager
from app.attendance_scheduler import AttendanceScheduler
from app.auth import authenticate_admin, get_current_admin
from app.calendar import CalendarService
from app.config import settings
from app.csrf import (
    CSRFMiddleware,
    csrf_context,
    rotate_csrf_token,
)
from app.database import get_db
from app.models import (
    Admin,
    AttendanceStatus,
    CalendarDayType,
    SchoolSettings,
    Student,
    StudentAttendance,
    StudentLeave,
)
from app.registration_session import RegistrationSession
from app.student import StudentManager
from app.timezone import school_today


# ============================================================
# ATTENDANCE SCHEDULER
# ============================================================

attendance_scheduler = AttendanceScheduler(
    camera_index=settings.attendance_camera_index,
    check_interval_seconds=30,
)

scheduler_thread: Thread | None = None


def start_attendance_scheduler():
    """
    Start the automatic attendance scheduler in a background
    daemon thread.
    """

    global scheduler_thread

    if (
        scheduler_thread is not None
        and scheduler_thread.is_alive()
    ):
        print(
            "Attendance scheduler is already running."
        )
        return

    print()
    print("========================================")
    print("   STARTING ATTENDANCE SCHEDULER")
    print("========================================")
    print(
        "Attendance scheduler will monitor the "
        "configured school attendance window."
    )
    print("========================================")
    print()

    scheduler_thread = Thread(
        target=attendance_scheduler.run_forever,
        name="attendance-scheduler",
        daemon=True,
    )

    scheduler_thread.start()


def stop_attendance_scheduler():
    """
    Stop the automatic attendance scheduler cleanly.
    """

    global scheduler_thread

    if scheduler_thread is None:
        return

    if not scheduler_thread.is_alive():
        scheduler_thread = None
        return

    print()
    print(
        "Stopping automatic attendance scheduler..."
    )

    # Request scheduler shutdown.
    #
    # stop() sets both:
    #   - running = False
    #   - stop_event = set()
    #
    # This immediately wakes the scheduler if it is
    # currently waiting between checks.
    attendance_scheduler.stop()

    scheduler_thread.join(timeout=5)

    if (
        attendance_scheduler.session_thread is not None
        and attendance_scheduler.session_thread.is_alive()
    ):
        attendance_scheduler.session_thread.join(timeout=5)

    if scheduler_thread.is_alive():
        print(
            "Attendance scheduler thread did not stop "
            "within the shutdown timeout."
        )
    else:
        print(
            "Attendance scheduler stopped successfully."
        )

    scheduler_thread = None


# ============================================================
# APPLICATION LIFESPAN
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI application lifecycle.

    Startup:
        Start automatic attendance scheduler.

    Shutdown:
        Stop scheduler cleanly.
    """

    start_attendance_scheduler()

    yield

    stop_attendance_scheduler()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


# ============================================================
# STATIC FILES (CSS, JS, images served from /static/...)
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


# ============================================================
# SESSION MIDDLEWARE
# ============================================================
#
# Middleware order note: Starlette runs the LAST added
# middleware first, so CSRFMiddleware is added before
# SessionMiddleware on purpose. That puts the session
# middleware on the outside, which is required — the CSRF
# check reads the session it decodes.

app.add_middleware(CSRFMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="face_attendance_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    # Set to True only when serving over HTTPS. On a plain
    # HTTP school LAN a Secure cookie is never sent, which
    # locks everyone out of the dashboard.
    https_only=False,
)


# ============================================================
# MANAGERS / SERVICES
# ============================================================

student_manager = StudentManager()
registration_session = RegistrationSession(
    camera_index=settings.registration_camera_index
)

attendance_manager = AttendanceManager()

calendar_service = CalendarService()

templates = Jinja2Templates(
    directory="templates",
    # Makes `csrf_token` available in every template without
    # each route having to pass it through.
    context_processors=[csrf_context],
)


# ============================================================
# FORM HELPERS
# ============================================================


def parse_form_date(
    value: str,
    label: str,
) -> date:
    """
    Parse a date submitted by a form.

    Raises ValueError with a clean, human-readable message.
    `date.fromisoformat` echoes the raw input back inside its
    own error text, which is both ugly and untrustworthy
    content to put in front of the user.
    """

    try:
        return date.fromisoformat(value.strip())

    except ValueError:
        raise ValueError(
            f"{label} is not a valid date. "
            "Please pick a date from the calendar."
        ) from None


def parse_day_type(value: str) -> CalendarDayType:
    """
    Parse a calendar day type submitted by a form, with a
    clean error message instead of the enum's default one.
    """

    try:
        return CalendarDayType(value.strip())

    except ValueError:
        allowed = ", ".join(
            item.value
            for item in CalendarDayType
        )

        raise ValueError(
            "Please choose a valid day type "
            f"({allowed})."
        ) from None


# ============================================================
# ADMIN LOGIN
# ============================================================


@app.get(
    "/login",
    response_class=HTMLResponse,
)
def login_page(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None,
        },
    )


@app.post(
    "/login",
    response_class=HTMLResponse,
)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()

    if not username:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Please enter your username.",
            },
            status_code=400,
        )

    if not password:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Please enter your password.",
            },
            status_code=400,
        )

    admin = authenticate_admin(
        db=db,
        username=username,
        password=password,
    )

    if admin is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid username or password.",
            },
            status_code=401,
        )

    request.session["admin_id"] = admin.id

    # Issue a fresh CSRF token now that the session is
    # authenticated, so a token handed out on the login page
    # cannot be reused against the logged-in session.
    rotate_csrf_token(request)

    return RedirectResponse(
        url="/",
        status_code=303,
    )


# ============================================================
# LOGOUT
# ============================================================


@app.post("/logout")
def logout(
    request: Request,
):
    request.session.clear()

    return RedirectResponse(
        url="/login",
        status_code=303,
    )


# ============================================================
# HOME / ADMIN DASHBOARD
# ============================================================


@app.get(
    "/",
    response_class=HTMLResponse,
)
def home(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Render the main admin dashboard.

    Attendance expectation hierarchy:

        1. School-wide calendar
        2. Class-specific calendar
        3. Student-specific leave
        4. Normal attendance expectation

    A student is EXPECTED only when:

        - the student is active
        - the school is not OFF
        - the student's class is not OFF
        - the student is not on approved leave

    Students excluded because of school/class calendar rules
    or approved student leave are NOT counted absent.
    """

    today = school_today()

    # ========================================================
    # TOTAL ACTIVE STUDENTS
    # ========================================================

    active_students = (
        db.query(Student)
        .filter(
            Student.is_active.is_(True)
        )
        .all()
    )

    total_students = len(active_students)

    active_student_ids = {
        student.id
        for student in active_students
    }

    # ========================================================
    # TODAY'S STUDENT LEAVE
    # ========================================================

    leave_records = (
        db.query(StudentLeave)
        .filter(
            StudentLeave.start_date <= today,
            StudentLeave.end_date >= today,
        )
        .all()
    )

    students_on_leave = {
        leave.student_id
        for leave in leave_records
        if leave.student_id in active_student_ids
    }

    leave_count = len(students_on_leave)

    # ========================================================
    # TODAY'S SCHOOL-WIDE CALENDAR STATUS
    # ========================================================

    school_calendar_entry = (
        calendar_service.get_school_calendar_day(
            db=db,
            target_date=today,
        )
    )

    calendar_off = (
        school_calendar_entry is not None
        and school_calendar_entry.is_off
    )

    calendar_title = (
        school_calendar_entry.title
        if school_calendar_entry is not None
        else None
    )

    calendar_day_type = (
        school_calendar_entry.day_type.value
        if school_calendar_entry is not None
        else None
    )

    # ========================================================
    # DETERMINE EXPECTED STUDENTS
    # ========================================================
    #
    # School-wide OFF:
    #
    #     Nobody is expected.
    #
    # Normal school day:
    #
    #     Student leave:
    #         Not expected
    #
    #     Class-specific OFF:
    #         Not expected
    #
    #     Otherwise:
    #         Expected
    #
    # ========================================================

    expected_student_ids = set()

    class_off_student_ids = set()

    calendar_off_student_ids = set()

    if calendar_off:

        # ----------------------------------------------------
        # SCHOOL-WIDE OFF
        # ----------------------------------------------------

        calendar_off_student_ids = {
            student.id
            for student in active_students
        }

    else:

        # ----------------------------------------------------
        # NORMAL SCHOOL DAY
        # ----------------------------------------------------

        for student in active_students:

            # ------------------------------------------------
            # STUDENT-SPECIFIC LEAVE
            # ------------------------------------------------

            if student.id in students_on_leave:
                continue

            # ------------------------------------------------
            # CLASS-SPECIFIC CALENDAR
            # ------------------------------------------------

            class_rule = (
                calendar_service.get_class_calendar_day(
                    db=db,
                    class_name=student.student_class,
                    target_date=today,
                )
            )

            if (
                class_rule is not None
                and class_rule.is_off
            ):
                class_off_student_ids.add(
                    student.id
                )
                continue

            # ------------------------------------------------
            # STUDENT IS EXPECTED
            # ------------------------------------------------

            expected_student_ids.add(
                student.id
            )

    # ========================================================
    # EXPECTED STUDENT COUNT
    # ========================================================

    expected_students = len(
        expected_student_ids
    )

    # ========================================================
    # NOT EXPECTED COUNT
    # ========================================================
    #
    # This includes ALL active students who are not expected:
    #
    #     - school-wide OFF
    #     - class-specific OFF
    #     - student-specific leave
    #
    # Therefore:
    #
    #     Expected + Not Expected = Total
    #
    # ========================================================

    not_expected_count = max(
        total_students - expected_students,
        0,
    )

    # Number of students excluded specifically because
    # their class is OFF today.
    class_off_count = len(
        class_off_student_ids
    )

    # Number of students excluded because the entire
    # school is OFF today.
    calendar_off_count = len(
        calendar_off_student_ids
    )

    # ========================================================
    # TODAY'S ATTENDANCE
    # ========================================================

    attendance_records = (
        db.query(StudentAttendance)
        .filter(
            StudentAttendance.date == today
        )
        .all()
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Only attendance belonging to EXPECTED students counts
    # toward present/late statistics.
    #
    # This prevents attendance from a student who is on leave
    # or whose class is OFF from inflating attendance.
    # --------------------------------------------------------

    present_count = sum(
        1
        for record in attendance_records
        if (
            record.status == AttendanceStatus.PRESENT
            and record.student_id in expected_student_ids
        )
    )

    late_count = sum(
        1
        for record in attendance_records
        if (
            record.status == AttendanceStatus.LATE
            and record.student_id in expected_student_ids
        )
    )

    # ========================================================
    # ATTENDED STUDENTS
    # ========================================================

    attended_students = (
        present_count
        + late_count
    )

    # ========================================================
    # ABSENT STUDENTS
    # ========================================================
    #
    # Only EXPECTED students can be absent.
    #
    # Therefore:
    #
    #     expected - attended
    #
    # Students on leave:
    #     NOT absent
    #
    # Class-off students:
    #     NOT absent
    #
    # School-off students:
    #     NOT absent
    #
    # ========================================================

    absent_count = max(
        expected_students - attended_students,
        0,
    )

    # ========================================================
    # ATTENDANCE RATE
    # ========================================================

    if expected_students > 0:

        attendance_rate = round(
            (
                attended_students
                / expected_students
            )
            * 100
        )

    else:

        attendance_rate = 0

    # ========================================================
    # RENDER DASHBOARD
    # ========================================================

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "admin": current_admin,

            # ------------------------------------------------
            # Student totals
            # ------------------------------------------------

            "total_students": total_students,

            # ------------------------------------------------
            # Attendance
            # ------------------------------------------------

            "present_count": present_count,
            "late_count": late_count,
            "leave_count": leave_count,
            "absent_count": absent_count,

            # ------------------------------------------------
            # Expected population
            # ------------------------------------------------

            "expected_students": expected_students,

            # ------------------------------------------------
            # Not expected population
            # ------------------------------------------------

            "not_expected_count": not_expected_count,
            "calendar_off_count": calendar_off_count,
            "class_off_count": class_off_count,

            # ------------------------------------------------
            # Attendance rate
            # ------------------------------------------------

            "attendance_rate": attendance_rate,

            # ------------------------------------------------
            # Calendar
            # ------------------------------------------------

            "calendar_off": calendar_off,
            "calendar_title": calendar_title,
            "calendar_day_type": calendar_day_type,
        },
    )


# ============================================================
# HEALTH CHECK
# ============================================================


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# ============================================================
# SCHEDULER STATUS
# ============================================================


@app.get("/scheduler/status")
def scheduler_status(
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Return the current automatic attendance scheduler status.
    """

    status = attendance_scheduler.get_status()

    return {
        "scheduler_running": attendance_scheduler.running,
        "scheduler_thread_alive": (
            scheduler_thread is not None
            and scheduler_thread.is_alive()
        ),
        "last_started_date": (
            attendance_scheduler.last_started_date.isoformat()
            if attendance_scheduler.last_started_date
            else None
        ),
        "should_start": status.get(
            "should_start"
        ),
        "reason": status.get(
            "reason"
        ),
        "date": (
            status["date"].isoformat()
            if status.get("date")
            else None
        ),
        "time": (
            status["time"].isoformat()
            if status.get("time")
            else None
        ),
        "calendar_allowed": status.get(
            "calendar_allowed"
        ),
        "calendar_reason": status.get(
            "calendar_reason"
        ),
        "calendar_title": status.get(
            "calendar_title"
        ),
        "calendar_day_type": (
            status["calendar_day_type"].value
            if hasattr(
                status.get("calendar_day_type"),
                "value",
            )
            else status.get(
                "calendar_day_type"
            )
        ),
    }


# ============================================================
# SCHOOL SETTINGS WEB PAGE
# ============================================================


@app.get(
    "/settings",
    response_class=HTMLResponse,
)
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Display the web-based School Settings page.

    A settings record is not created automatically here.
    If none exists, the page displays an unconfigured state
    and allows the administrator to create it by saving.
    """

    school_settings = (
        db.query(SchoolSettings)
        .order_by(SchoolSettings.id)
        .first()
    )

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "admin": current_admin,
            "settings": school_settings,
            "configured": school_settings is not None,
            "error": None,
            "success": None,
        },
    )


# ============================================================
# SAVE SCHOOL SETTINGS
# ============================================================


@app.post(
    "/settings",
    response_class=HTMLResponse,
)
def save_settings(
    request: Request,
    school_name: str = Form(...),
    attendance_start_time: str = Form(...),
    attendance_end_time: str = Form(...),
    late_after_minutes: str = Form(...),
    timezone: str = Form(...),
    report_email: str = Form(""),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Create or update the single SchoolSettings record.
    """

    school_name = school_name.strip()
    attendance_start_time = (
        attendance_start_time.strip()
    )
    attendance_end_time = (
        attendance_end_time.strip()
    )
    late_after_minutes = (
        late_after_minutes.strip()
    )
    timezone = timezone.strip()
    report_email = report_email.strip()

    school_settings = (
        db.query(SchoolSettings)
        .order_by(SchoolSettings.id)
        .first()
    )

    form_data = {
        "school_name": school_name,
        "attendance_start_time": (
            attendance_start_time
        ),
        "attendance_end_time": (
            attendance_end_time
        ),
        "late_after_minutes": (
            late_after_minutes
        ),
        "timezone": timezone,
        "report_email": report_email,
    }

    # --------------------------------------------------------
    # SCHOOL NAME
    # --------------------------------------------------------

    if not school_name:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "admin": current_admin,
                "settings": school_settings,
                "configured": school_settings is not None,
                "error": "School name cannot be empty.",
                "success": None,
                "form": form_data,
            },
            status_code=400,
        )

    # --------------------------------------------------------
    # START TIME
    # --------------------------------------------------------

    try:
        parsed_start_time = datetime.strptime(
            attendance_start_time,
            "%H:%M",
        ).time()

    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "admin": current_admin,
                "settings": school_settings,
                "configured": school_settings is not None,
                "error": (
                    "Invalid attendance start time. "
                    "Use HH:MM format, for example 08:00."
                ),
                "success": None,
                "form": form_data,
            },
            status_code=400,
        )

    # --------------------------------------------------------
    # END TIME
    # --------------------------------------------------------

    try:
        parsed_end_time = datetime.strptime(
            attendance_end_time,
            "%H:%M",
        ).time()

    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "admin": current_admin,
                "settings": school_settings,
                "configured": school_settings is not None,
                "error": (
                    "Invalid attendance end time. "
                    "Use HH:MM format, for example 10:00."
                ),
                "success": None,
                "form": form_data,
            },
            status_code=400,
        )

    # --------------------------------------------------------
    # ATTENDANCE WINDOW
    # --------------------------------------------------------

    if parsed_start_time >= parsed_end_time:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "admin": current_admin,
                "settings": school_settings,
                "configured": school_settings is not None,
                "error": (
                    "Attendance start time must be earlier "
                    "than attendance end time."
                ),
                "success": None,
                "form": form_data,
            },
            status_code=400,
        )

    # --------------------------------------------------------
    # LATE THRESHOLD
    # --------------------------------------------------------

    try:
        parsed_late_after = int(
            late_after_minutes
        )

        if parsed_late_after < 0:
            raise ValueError

    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "admin": current_admin,
                "settings": school_settings,
                "configured": school_settings is not None,
                "error": (
                    "Late-after minutes must be a "
                    "non-negative whole number."
                ),
                "success": None,
                "form": form_data,
            },
            status_code=400,
        )

    # --------------------------------------------------------
    # TIMEZONE
    # --------------------------------------------------------

    if not timezone:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "admin": current_admin,
                "settings": school_settings,
                "configured": school_settings is not None,
                "error": "Timezone cannot be empty.",
                "success": None,
                "form": form_data,
            },
            status_code=400,
        )

    # --------------------------------------------------------
    # REPORT EMAIL
    # --------------------------------------------------------

    if report_email:
        if "@" not in report_email:
            return templates.TemplateResponse(
                request=request,
                name="settings.html",
                context={
                    "admin": current_admin,
                    "settings": school_settings,
                    "configured": school_settings is not None,
                    "error": (
                        "Please enter a valid report email "
                        "address or leave it empty."
                    ),
                    "success": None,
                    "form": form_data,
                },
                status_code=400,
            )

    # --------------------------------------------------------
    # CREATE OR UPDATE
    # --------------------------------------------------------

    try:

        if school_settings is None:

            school_settings = SchoolSettings()

            db.add(
                school_settings
            )

        school_settings.school_name = (
            school_name
        )

        school_settings.attendance_start_time = (
            parsed_start_time
        )

        school_settings.attendance_end_time = (
            parsed_end_time
        )

        school_settings.late_after_minutes = (
            parsed_late_after
        )

        school_settings.timezone = (
            timezone
        )

        school_settings.report_email = (
            report_email
            if report_email
            else None
        )

        db.commit()

        db.refresh(
            school_settings
        )

    except Exception as error:

        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "admin": current_admin,
                "settings": school_settings,
                "configured": school_settings is not None,
                "error": (
                    "Could not save school settings: "
                    f"{error}"
                ),
                "success": None,
                "form": form_data,
            },
            status_code=500,
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return RedirectResponse(
        url="/settings?saved=1",
        status_code=303,
    )


# ============================================================
# SCHOOL SETTINGS STATUS
# ============================================================


@app.get("/settings/status")
def settings_status(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Return currently configured school attendance settings.
    """

    school_settings = (
        db.query(SchoolSettings)
        .order_by(SchoolSettings.id)
        .first()
    )

    if school_settings is None:
        return {
            "configured": False,
            "message": (
                "School attendance settings "
                "have not been configured."
            ),
        }

    return {
        "configured": True,
        "school_name": school_settings.school_name,
        "attendance_start_time": (
            school_settings.attendance_start_time.isoformat()
        ),
        "attendance_end_time": (
            school_settings.attendance_end_time.isoformat()
        ),
        "late_after_minutes": (
            school_settings.late_after_minutes
        ),
        "timezone": school_settings.timezone,
        "report_email": school_settings.report_email,
    }


# ============================================================
# STUDENTS API
# ============================================================


@app.get("/students")
def get_students(
    current_admin: Admin = Depends(get_current_admin),
):
    students = student_manager.get_all_students()

    return [
        {
            "student_id": student["student_id"],
            "name": student["name"],
            "class": student["class"],
        }
        for student in students
    ]


# ============================================================
# STUDENT DELETE
# ============================================================


@app.post("/students/{student_id}/delete")
def delete_student(
    student_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    deleted = student_manager.delete_student(student_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Student not found.",
        )

    return {"status": "deleted"}


# ============================================================
# STUDENT REGISTRATION (camera capture via web UI)
# ============================================================


@app.post("/students/register/start")
def start_student_registration(
    current_admin: Admin = Depends(get_current_admin),
):
    # Only the two capture sessions can conflict if they're
    # actually configured to use the same physical camera
    # (e.g. during testing with a single webcam). Once a
    # dedicated registration camera is configured, this check
    # is a no-op.
    same_camera = (
        settings.registration_camera_index
        == settings.attendance_camera_index
    )

    if same_camera and attendance_scheduler.is_session_active():
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot start registration right now — the "
                "automatic attendance session is currently "
                "using this camera. Try again after the "
                "attendance window closes, or configure a "
                "separate registration camera in settings."
            ),
        )

    try:
        registration_session.start()
    except RuntimeError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    return {"status": "started"}


@app.get("/students/register/stream")
def student_registration_stream(
    current_admin: Admin = Depends(get_current_admin),
):
    def generate():
        # Cap the stream at roughly this rate. Without a pause
        # the loop encodes JPEGs as fast as the CPU allows and
        # pegs a core for the whole registration.
        frame_interval_seconds = 1 / 20

        while True:
            frame_started_at = time.monotonic()

            frame = registration_session.get_jpeg_frame()

            if frame is None:
                break

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame
                + b"\r\n"
            )

            elapsed = (
                time.monotonic() - frame_started_at
            )

            remaining = (
                frame_interval_seconds - elapsed
            )

            if remaining > 0:
                time.sleep(remaining)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/students/register/status")
def student_registration_status(
    current_admin: Admin = Depends(get_current_admin),
):
    return registration_session.status()


@app.post("/students/register/save")
def save_student_registration(
    name: str = Form(...),
    student_class: str = Form(...),
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        student = registration_session.save(
            name=name,
            student_class=student_class,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    return {
        "student_id": student["student_id"],
        "name": student["name"],
        "class": student["class"],
    }


@app.post("/students/register/cancel")
def cancel_student_registration(
    current_admin: Admin = Depends(get_current_admin),
):
    registration_session.cancel()

    return {"status": "cancelled"}


# ============================================================
# STUDENTS PAGE
# ============================================================


@app.get(
    "/students/page",
    response_class=HTMLResponse,
)
def students_page(
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "admin": current_admin,
        },
    )


# ============================================================
# TODAY'S ATTENDANCE API
# ============================================================


@app.get("/attendance/today")
def get_today_attendance(
    current_admin: Admin = Depends(get_current_admin),
):
    today = school_today().isoformat()

    return attendance_manager.load_daily_attendance(
        today
    )


# ============================================================
# ATTENDANCE PAGE
# ============================================================


@app.get(
    "/attendance",
    response_class=HTMLResponse,
)
def attendance_page(
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="attendance.html",
        context={
            "admin": current_admin,
        },
    )


# ============================================================
# ATTENDANCE HISTORY PAGE
# ============================================================


@app.get(
    "/attendance/history",
    response_class=HTMLResponse,
)
def attendance_history_page(
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="attendance_history.html",
        context={
            "admin": current_admin,
        },
    )


# ============================================================
# ATTENDANCE REPORT PAGE
# ============================================================


@app.get(
    "/attendance/report",
    response_class=HTMLResponse,
)
def attendance_report_page(
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="attendance_report.html",
        context={
            "admin": current_admin,
        },
    )


# ============================================================
# ATTENDANCE REPORT API
# ============================================================


@app.get("/attendance/report/{report_date}")
def get_attendance_report(
    report_date: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Generate the attendance report for a specific date.

    IMPORTANT:
        The route parameter is intentionally called
        `report_date` so it does not shadow the imported
        `datetime.date` class.
    """

    try:
        parsed_date = date.fromisoformat(
            report_date
        )

    except ValueError:
        return {
            "error": (
                "Invalid date format. "
                "Expected YYYY-MM-DD."
            )
        }

    return attendance_manager.generate_report(
        parsed_date
    )


# ============================================================
# ATTENDANCE BY DATE API
# ============================================================

@app.delete("/attendance/record/{attendance_id}")
def delete_attendance_record(
    attendance_id: int,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete one attendance record.

    Admin authentication is required.
    """

    deleted = attendance_manager.delete_attendance_record(
        attendance_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Attendance record not found.",
        )

    return {
        "success": True,
        "deleted_id": attendance_id,
    }

@app.get("/attendance/{attendance_date}")
def get_attendance_by_date(
    attendance_date: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Load attendance records for a specific date.
    """

    return attendance_manager.load_daily_attendance(
        attendance_date
    )


# ============================================================
# CALENDAR MANAGEMENT PAGE
# ============================================================


def render_calendar_page(
    request: Request,
    db: Session,
    current_admin: Admin,
    error: str | None = None,
    status_code: int = 200,
):
    """
    Render the calendar page.

    Shared by the GET route and by the create/delete routes
    when they need to report a problem, so error text always
    goes through Jinja2 (which escapes it) instead of being
    pasted into raw HTML.
    """

    school_calendar = (
        calendar_service.get_school_calendar(
            db=db,
        )
    )

    class_calendar = (
        calendar_service.get_all_class_calendar(
            db=db,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="calendar.html",
        context={
            "admin": current_admin,
            "school_calendar": school_calendar,
            "class_calendar": class_calendar,
            "error": error,
        },
        status_code=status_code,
    )


@app.get(
    "/calendar",
    response_class=HTMLResponse,
)
def calendar_page(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    return render_calendar_page(
        request=request,
        db=db,
        current_admin=current_admin,
    )


# ============================================================
# CREATE SCHOOL-WIDE CALENDAR ENTRY
# ============================================================


@app.post("/calendar/school")
def create_school_calendar(
    request: Request,
    start_date: str = Form(...),
    end_date: str = Form(...),
    title: str = Form(...),
    day_type: str = Form(...),
    is_off: str = Form(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        title = title.strip()

        if not title:
            raise ValueError(
                "Calendar title cannot be empty."
            )

        parsed_start_date = parse_form_date(
            start_date,
            "Start date",
        )

        parsed_end_date = parse_form_date(
            end_date,
            "End date",
        )

        if parsed_end_date < parsed_start_date:
            raise ValueError(
                "End date cannot be before start date."
            )

        parsed_day_type = parse_day_type(day_type)

        parsed_is_off = (
            is_off.lower() == "true"
        )

        calendar_service.create_school_calendar(
            db=db,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            title=title,
            day_type=parsed_day_type,
            is_off=parsed_is_off,
        )

    except ValueError as exc:
        return render_calendar_page(
            request=request,
            db=db,
            current_admin=current_admin,
            error=str(exc),
            status_code=400,
        )

    return RedirectResponse(
        url="/calendar",
        status_code=303,
    )


# ============================================================
# DELETE SCHOOL-WIDE CALENDAR ENTRY
# ============================================================


@app.post(
    "/calendar/school/{calendar_id}/delete"
)
def delete_school_calendar(
    request: Request,
    calendar_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    deleted = (
        calendar_service.delete_school_calendar(
            db=db,
            calendar_id=calendar_id,
        )
    )

    if not deleted:
        return render_calendar_page(
            request=request,
            db=db,
            current_admin=current_admin,
            error=(
                "That school calendar entry no longer "
                "exists — it may already have been "
                "deleted."
            ),
            status_code=404,
        )

    return RedirectResponse(
        url="/calendar",
        status_code=303,
    )


# ============================================================
# CREATE CLASS-SPECIFIC CALENDAR ENTRY
# ============================================================


@app.post("/calendar/class")
def create_class_calendar(
    request: Request,
    class_name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    title: str = Form(...),
    day_type: str = Form(...),
    is_off: str = Form(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        class_name = class_name.strip()
        title = title.strip()

        if not class_name:
            raise ValueError(
                "Class name cannot be empty."
            )

        if not title:
            raise ValueError(
                "Calendar title cannot be empty."
            )

        parsed_start_date = parse_form_date(
            start_date,
            "Start date",
        )

        parsed_end_date = parse_form_date(
            end_date,
            "End date",
        )

        if parsed_end_date < parsed_start_date:
            raise ValueError(
                "End date cannot be before start date."
            )

        parsed_day_type = parse_day_type(day_type)

        parsed_is_off = (
            is_off.lower() == "true"
        )

        calendar_service.create_class_calendar(
            db=db,
            class_name=class_name,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            title=title,
            day_type=parsed_day_type,
            is_off=parsed_is_off,
        )

    except ValueError as exc:
        return render_calendar_page(
            request=request,
            db=db,
            current_admin=current_admin,
            error=str(exc),
            status_code=400,
        )

    return RedirectResponse(
        url="/calendar",
        status_code=303,
    )


# ============================================================
# DELETE CLASS-SPECIFIC CALENDAR ENTRY
# ============================================================


@app.post(
    "/calendar/class/{calendar_id}/delete"
)
def delete_class_calendar(
    request: Request,
    calendar_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    deleted = (
        calendar_service.delete_class_calendar(
            db=db,
            calendar_id=calendar_id,
        )
    )

    if not deleted:
        return render_calendar_page(
            request=request,
            db=db,
            current_admin=current_admin,
            error=(
                "That class calendar entry no longer "
                "exists — it may already have been "
                "deleted."
            ),
            status_code=404,
        )

    return RedirectResponse(
        url="/calendar",
        status_code=303,
    )


# ============================================================
# STUDENT LEAVE MANAGEMENT
# ============================================================


@app.get(
    "/leaves",
    response_class=HTMLResponse,
)
def student_leaves_page(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    return render_leaves_page(
        request=request,
        db=db,
        current_admin=current_admin,
    )


def render_leaves_page(
    request: Request,
    db: Session,
    current_admin: Admin,
    error: str | None = None,
    status_code: int = 200,
):
    """
    Render the student leaves page.

    Shared by the GET route and by the create/delete routes so
    error text is escaped by Jinja2 rather than injected into
    raw HTML.
    """

    students = (
        db.query(Student)
        .filter(Student.is_active.is_(True))
        .order_by(Student.name)
        .all()
    )

    leaves = (
        db.query(StudentLeave)
        .order_by(
            StudentLeave.start_date.desc(),
            StudentLeave.id.desc(),
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="student_leaves.html",
        context={
            "admin": current_admin,
            "students": students,
            "leaves": leaves,
            "error": error,
        },
        status_code=status_code,
    )


@app.post("/leaves")
def create_student_leave(
    request: Request,
    student_id: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    reason: str = Form(""),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        student = (
            db.query(Student)
            .filter(
                Student.id == student_id,
                Student.is_active.is_(True),
            )
            .first()
        )

        if student is None:
            raise ValueError(
                "That student could not be found. "
                "Please pick a student from the list."
            )

        parsed_start_date = parse_form_date(
            start_date,
            "Start date",
        )

        parsed_end_date = parse_form_date(
            end_date,
            "End date",
        )

        if parsed_end_date < parsed_start_date:
            raise ValueError(
                "End date cannot be before start date."
            )

        leave = StudentLeave(
            student_id=student.id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            reason=reason.strip() or None,
        )

        db.add(leave)
        db.commit()

    except ValueError as exc:
        db.rollback()

        return render_leaves_page(
            request=request,
            db=db,
            current_admin=current_admin,
            error=str(exc),
            status_code=400,
        )

    return RedirectResponse(
        url="/leaves",
        status_code=303,
    )


@app.post("/leaves/{leave_id}/delete")
def delete_student_leave(
    request: Request,
    leave_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    leave = (
        db.query(StudentLeave)
        .filter(StudentLeave.id == leave_id)
        .first()
    )

    if leave is None:
        return render_leaves_page(
            request=request,
            db=db,
            current_admin=current_admin,
            error=(
                "That leave record no longer exists — it "
                "may already have been deleted."
            ),
            status_code=404,
        )

    db.delete(leave)
    db.commit()

    return RedirectResponse(
        url="/leaves",
        status_code=303,
    )


# ============================================================
# SERVER START
# ============================================================


if __name__ == "__main__":
    print()
    print("========================================")
    print("   FACE ATTENDANCE SERVER")
    print("========================================")
    print(
        "Listening on "
        f"{settings.server_host}:{settings.server_port}"
    )

    if settings.server_host == "0.0.0.0":
        print(
            "Other devices on this network can open:"
        )
        print(
            "    http://<this-pc-ip>:"
            f"{settings.server_port}"
        )
        print(
            "Run 'ipconfig' to find this machine's IP."
        )

    print("========================================")
    print()

    uvicorn.run(
        "server:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
    )