from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.models import SchoolSettings


DEFAULT_TIMEZONE = "Asia/Karachi"


def get_school_timezone() -> ZoneInfo:
    """
    Return the configured school timezone.

    Falls back to Asia/Karachi if no settings record
    exists or the configured timezone is invalid.
    """

    db = SessionLocal()

    try:
        settings = (
            db.query(SchoolSettings)
            .order_by(SchoolSettings.id)
            .first()
        )

        timezone_name = (
            settings.timezone
            if settings and settings.timezone
            else DEFAULT_TIMEZONE
        )

        try:
            return ZoneInfo(timezone_name)
        except Exception:
            return ZoneInfo(DEFAULT_TIMEZONE)

    finally:
        db.close()


def school_now() -> datetime:
    """
    Return the current datetime in the configured
    school timezone.
    """

    return datetime.now(get_school_timezone())


def school_today():
    """
    Return today's date in the configured school timezone.
    """

    return school_now().date()