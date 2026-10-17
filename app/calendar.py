from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CalendarDayType,
    ClassCalendar,
    SchoolCalendar,
)


class CalendarService:
    """
    Handles school-wide and class-specific calendar rules.

    Calendar hierarchy:

        School-wide calendar
                ↓
        Class-specific calendar
                ↓
        Attendance decision

    Rules:

    1. A calendar entry applies when:

           start_date <= target_date <= end_date

    2. School-wide OFF rules take priority over
       class-specific rules.

    3. A one-day event is represented by:

           start_date == end_date

    4. Date ranges are inclusive.

    Example:

        2026-08-20 → 2026-08-20
        means only August 20 is affected.

        2026-08-20 → 2026-08-25
        means August 20 through August 25 are affected.
    """

    # ========================================================
    # INTERNAL VALIDATION HELPERS
    # ========================================================

    @staticmethod
    def _validate_date_range(
        start_date: date,
        end_date: date,
    ) -> None:
        """
        Validate a calendar date range.
        """

        if not isinstance(start_date, date):
            raise ValueError(
                "Start date must be a valid date."
            )

        if not isinstance(end_date, date):
            raise ValueError(
                "End date must be a valid date."
            )

        if end_date < start_date:
            raise ValueError(
                "End date cannot be before start date."
            )

    @staticmethod
    def _validate_title(title: str) -> str:
        """
        Normalize and validate a calendar title.
        """

        if title is None:
            raise ValueError(
                "Calendar title cannot be empty."
            )

        title = title.strip()

        if not title:
            raise ValueError(
                "Calendar title cannot be empty."
            )

        return title

    @staticmethod
    def _validate_class_name(
        class_name: str,
    ) -> str:
        """
        Normalize and validate a class name.
        """

        if class_name is None:
            raise ValueError(
                "Class name cannot be empty."
            )

        class_name = class_name.strip()

        if not class_name:
            raise ValueError(
                "Class name cannot be empty."
            )

        return class_name

    # ========================================================
    # SCHOOL-WIDE CALENDAR
    # ========================================================

    def get_school_calendar_day(
        self,
        db: Session,
        target_date: date,
    ) -> SchoolCalendar | None:
        """
        Return the school-wide calendar rule that applies
        to the requested date.

        A rule applies when:

            start_date <= target_date <= end_date

        If multiple entries somehow exist, the most recently
        starting entry is returned.
        """

        return db.scalar(
            select(SchoolCalendar)
            .where(
                SchoolCalendar.start_date <= target_date,
                SchoolCalendar.end_date >= target_date,
            )
            .order_by(
                SchoolCalendar.start_date.desc(),
                SchoolCalendar.id.desc(),
            )
        )

    def get_school_calendar(
        self,
        db: Session,
    ) -> list[SchoolCalendar]:
        """
        Return all school-wide calendar entries.
        """

        return list(
            db.scalars(
                select(SchoolCalendar).order_by(
                    SchoolCalendar.start_date,
                    SchoolCalendar.end_date,
                    SchoolCalendar.id,
                )
            )
        )

    def create_school_calendar(
        self,
        db: Session,
        start_date: date,
        end_date: date,
        title: str,
        day_type: CalendarDayType,
        is_off: bool = True,
    ) -> SchoolCalendar:
        """
        Create a school-wide calendar entry.

        One day:

            start_date == end_date

        Date range:

            start_date < end_date
        """

        self._validate_date_range(
            start_date=start_date,
            end_date=end_date,
        )

        title = self._validate_title(title)

        # ----------------------------------------------------
        # Prevent overlapping school-wide entries.
        #
        # Example:
        #
        # Existing: 20 → 25
        # New:      23 → 28
        #
        # This is rejected.
        # ----------------------------------------------------

        overlapping = db.scalar(
            select(SchoolCalendar)
            .where(
                SchoolCalendar.start_date <= end_date,
                SchoolCalendar.end_date >= start_date,
            )
        )

        if overlapping is not None:
            raise ValueError(
                "This date range overlaps an existing "
                "school-wide calendar entry."
            )

        entry = SchoolCalendar(
            start_date=start_date,
            end_date=end_date,
            title=title,
            day_type=day_type,
            is_off=bool(is_off),
            created_at=datetime.now(timezone.utc),
        )

        try:
            db.add(entry)
            db.commit()
            db.refresh(entry)

        except Exception:
            db.rollback()
            raise

        return entry

    def delete_school_calendar(
        self,
        db: Session,
        calendar_id: int,
    ) -> bool:
        """
        Delete a school-wide calendar entry.
        """

        entry = db.get(
            SchoolCalendar,
            calendar_id,
        )

        if entry is None:
            return False

        try:
            db.delete(entry)
            db.commit()

        except Exception:
            db.rollback()
            raise

        return True

    # ========================================================
    # CLASS-SPECIFIC CALENDAR
    # ========================================================

    def get_class_calendar_entries(
        self,
        db: Session,
        class_name: str,
        target_date: date,
    ) -> list[ClassCalendar]:
        """
        Return all class-specific calendar entries that
        apply to the class on the requested date.
        """

        class_name = self._validate_class_name(
            class_name
        )

        return list(
            db.scalars(
                select(ClassCalendar)
                .where(
                    ClassCalendar.class_name == class_name,
                    ClassCalendar.start_date <= target_date,
                    ClassCalendar.end_date >= target_date,
                )
                .order_by(
                    ClassCalendar.start_date,
                    ClassCalendar.id,
                )
            )
        )

    def get_class_calendar_day(
        self,
        db: Session,
        class_name: str,
        target_date: date,
    ) -> ClassCalendar | None:
        """
        Return the class-specific calendar rule that applies
        to the requested class and date.

        Returns the most recently starting applicable rule
        if multiple records somehow exist.
        """

        class_name = self._validate_class_name(
            class_name
        )

        return db.scalar(
            select(ClassCalendar)
            .where(
                ClassCalendar.class_name == class_name,
                ClassCalendar.start_date <= target_date,
                ClassCalendar.end_date >= target_date,
            )
            .order_by(
                ClassCalendar.start_date.desc(),
                ClassCalendar.id.desc(),
            )
        )

    def get_all_class_calendar(
        self,
        db: Session,
    ) -> list[ClassCalendar]:
        """
        Return all class-specific calendar entries.
        """

        return list(
            db.scalars(
                select(ClassCalendar).order_by(
                    ClassCalendar.start_date,
                    ClassCalendar.end_date,
                    ClassCalendar.class_name,
                    ClassCalendar.id,
                )
            )
        )

    def create_class_calendar(
        self,
        db: Session,
        class_name: str,
        start_date: date,
        end_date: date,
        title: str,
        day_type: CalendarDayType,
        is_off: bool = True,
    ) -> ClassCalendar:
        """
        Create a class-specific calendar entry.

        One-day event:

            start_date == end_date
        """

        class_name = self._validate_class_name(
            class_name
        )

        title = self._validate_title(title)

        self._validate_date_range(
            start_date=start_date,
            end_date=end_date,
        )

        # ----------------------------------------------------
        # Prevent overlapping entries for the same class.
        # ----------------------------------------------------

        overlapping = db.scalar(
            select(ClassCalendar).where(
                ClassCalendar.class_name == class_name,
                ClassCalendar.start_date <= end_date,
                ClassCalendar.end_date >= start_date,
            )
        )

        if overlapping is not None:
            raise ValueError(
                "This date range overlaps an existing "
                f"calendar entry for class {class_name}."
            )

        entry = ClassCalendar(
            class_name=class_name,
            start_date=start_date,
            end_date=end_date,
            title=title,
            day_type=day_type,
            is_off=bool(is_off),
            created_at=datetime.now(timezone.utc),
        )

        try:
            db.add(entry)
            db.commit()
            db.refresh(entry)

        except Exception:
            db.rollback()
            raise

        return entry

    def delete_class_calendar(
        self,
        db: Session,
        calendar_id: int,
    ) -> bool:
        """
        Delete a class-specific calendar entry.
        """

        entry = db.get(
            ClassCalendar,
            calendar_id,
        )

        if entry is None:
            return False

        try:
            db.delete(entry)
            db.commit()

        except Exception:
            db.rollback()
            raise

        return True

    # ========================================================
    # ATTENDANCE RULE RESOLUTION
    # ========================================================

    def get_attendance_rule(
        self,
        db: Session,
        class_name: str,
        target_date: date,
    ) -> dict:
        """
        Resolve the complete attendance rule for a class
        on a specific date.

        This gives the attendance system more information
        than a simple True/False value.

        Possible result:

            {
                "allowed": False,
                "source": "school",
                "day_type": "HOLIDAY",
                "title": "Independence Day",
                "is_off": True,
            }

        Or:

            {
                "allowed": True,
                "source": "default",
                "day_type": None,
                "title": None,
                "is_off": False,
            }
        """

        class_name = self._validate_class_name(
            class_name
        )

        # ----------------------------------------------------
        # 1. SCHOOL-WIDE RULE
        # ----------------------------------------------------

        school_rule = self.get_school_calendar_day(
            db=db,
            target_date=target_date,
        )

        if school_rule is not None:
            return {
                "allowed": not school_rule.is_off,
                "source": "school",
                "day_type": school_rule.day_type.value,
                "title": school_rule.title,
                "is_off": school_rule.is_off,
            }

        # ----------------------------------------------------
        # 2. CLASS-SPECIFIC RULE
        # ----------------------------------------------------

        class_rule = self.get_class_calendar_day(
            db=db,
            class_name=class_name,
            target_date=target_date,
        )

        if class_rule is not None:
            return {
                "allowed": not class_rule.is_off,
                "source": "class",
                "day_type": class_rule.day_type.value,
                "title": class_rule.title,
                "is_off": class_rule.is_off,
            }

        # ----------------------------------------------------
        # 3. NO SPECIAL RULE
        # ----------------------------------------------------

        return {
            "allowed": True,
            "source": "default",
            "day_type": None,
            "title": None,
            "is_off": False,
        }

    # ========================================================
    # SIMPLE ATTENDANCE CHECKS
    # ========================================================

    def is_school_off(
        self,
        db: Session,
        target_date: date,
    ) -> bool:
        """
        Determine whether the entire school is OFF.

        Any school-wide calendar rule with is_off=True
        closes attendance for everyone.
        """

        school_rule = self.get_school_calendar_day(
            db=db,
            target_date=target_date,
        )

        if school_rule is None:
            return False

        return bool(school_rule.is_off)

    def is_class_off(
        self,
        db: Session,
        class_name: str,
        target_date: date,
    ) -> bool:
        """
        Determine whether a particular class is OFF.

        School-wide rules take priority.
        """

        rule = self.get_attendance_rule(
            db=db,
            class_name=class_name,
            target_date=target_date,
        )

        return bool(rule["is_off"])

    def can_have_attendance(
        self,
        db: Session,
        class_name: str,
        target_date: date,
    ) -> bool:
        """
        Return True when attendance is allowed for the
        specified class on the specified date.
        """

        rule = self.get_attendance_rule(
            db=db,
            class_name=class_name,
            target_date=target_date,
        )

        return bool(rule["allowed"])