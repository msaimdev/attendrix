import tkinter as tk
from tkinter import messagebox
from datetime import time

from app.database import SessionLocal
from app.models import SchoolSettings


# ============================================================
# COLORS
# ============================================================

BG_COLOR = "#F5F8FC"
CARD_COLOR = "#FFFFFF"

TEXT_PRIMARY = "#172033"
TEXT_SECONDARY = "#64748B"

PRIMARY = "#3B82F6"
PRIMARY_HOVER = "#2563EB"

BORDER = "#E2E8F0"
SUCCESS = "#16A34A"


# ============================================================
# SETTINGS WINDOW
# ============================================================


class SettingsWindow:

    def __init__(self, parent):

        self.parent = parent

        self.window = tk.Toplevel(parent)

        self.window.title("School Settings")
        self.window.geometry("700x720")
        self.window.minsize(650, 650)

        self.window.configure(
            bg=BG_COLOR
        )

        self.window.transient(parent)
        self.window.grab_set()

        self._build_ui()
        self._load_settings()

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self):

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = tk.Frame(
            self.window,
            bg=BG_COLOR,
        )

        header.pack(
            fill="x",
            padx=40,
            pady=(30, 20),
        )

        title = tk.Label(
            header,
            text="School Settings",
            font=("Segoe UI", 22, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_COLOR,
            anchor="w",
        )

        title.pack(
            fill="x",
        )

        subtitle = tk.Label(
            header,
            text=(
                "Configure your school's attendance schedule "
                "and system settings."
            ),
            font=("Segoe UI", 10),
            fg=TEXT_SECONDARY,
            bg=BG_COLOR,
            anchor="w",
        )

        subtitle.pack(
            fill="x",
            pady=(6, 0),
        )

        # ----------------------------------------------------
        # CARD
        # ----------------------------------------------------

        card = tk.Frame(
            self.window,
            bg=CARD_COLOR,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30),
        )

        content = tk.Frame(
            card,
            bg=CARD_COLOR,
        )

        content.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=30,
        )

        # ----------------------------------------------------
        # SCHOOL NAME
        # ----------------------------------------------------

        self._label(
            content,
            "School Name",
        )

        self.school_name_entry = self._entry(
            content
        )

        self._hint(
            content,
            "The name displayed by the attendance system.",
        )

        # ----------------------------------------------------
        # ATTENDANCE START
        # ----------------------------------------------------

        self._label(
            content,
            "Attendance Start Time",
        )

        self.start_time_entry = self._entry(
            content
        )

        self._hint(
            content,
            "Required. 24-hour format. Example: 08:00",
        )

        # ----------------------------------------------------
        # ATTENDANCE END
        # ----------------------------------------------------

        self._label(
            content,
            "Attendance End Time",
        )

        self.end_time_entry = self._entry(
            content
        )

        self._hint(
            content,
            "Required. Attendance stops being eligible after this time.",
        )

        # ----------------------------------------------------
        # LATE THRESHOLD
        # ----------------------------------------------------

        self._label(
            content,
            "Late After (minutes)",
        )

        self.late_entry = self._entry(
            content
        )

        self._hint(
            content,
            "Required. Enter 0 to disable late tracking.",
        )

        # ----------------------------------------------------
        # TIMEZONE
        # ----------------------------------------------------

        self._label(
            content,
            "Timezone",
        )

        self.timezone_entry = self._entry(
            content
        )

        self._hint(
            content,
            "Required. Example: Asia/Karachi",
        )

        # ----------------------------------------------------
        # REPORT EMAIL
        # ----------------------------------------------------

        self._label(
            content,
            "Daily Report Email",
        )

        self.email_entry = self._entry(
            content
        )

        self._hint(
            content,
            "Optional. Used when daily attendance reports are enabled.",
        )

        # ----------------------------------------------------
        # CURRENT WINDOW PREVIEW
        # ----------------------------------------------------

        preview_frame = tk.Frame(
            content,
            bg="#F8FAFC",
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        preview_frame.pack(
            fill="x",
            pady=(25, 0),
        )

        preview_title = tk.Label(
            preview_frame,
            text="Attendance Window",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_SECONDARY,
            bg="#F8FAFC",
            anchor="w",
        )

        preview_title.pack(
            fill="x",
            padx=15,
            pady=(12, 3),
        )

        self.preview_label = tk.Label(
            preview_frame,
            text="--:-- - --:--",
            font=("Segoe UI", 16, "bold"),
            fg=PRIMARY,
            bg="#F8FAFC",
            anchor="w",
        )

        self.preview_label.pack(
            fill="x",
            padx=15,
            pady=(0, 12),
        )

        self.start_time_entry.bind(
            "<KeyRelease>",
            lambda event: self._update_preview(),
        )

        self.end_time_entry.bind(
            "<KeyRelease>",
            lambda event: self._update_preview(),
        )

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        buttons = tk.Frame(
            content,
            bg=CARD_COLOR,
        )

        buttons.pack(
            fill="x",
            pady=(25, 0),
        )

        cancel_button = tk.Button(
            buttons,
            text="Cancel",
            command=self.window.destroy,
            font=("Segoe UI", 10, "bold"),
            fg=TEXT_PRIMARY,
            bg="#EEF3FA",
            activeforeground=TEXT_PRIMARY,
            activebackground="#E2EAF5",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=11,
        )

        cancel_button.pack(
            side="left",
        )

        save_button = tk.Button(
            buttons,
            text="Save Settings",
            command=self.save_settings,
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=PRIMARY,
            activeforeground="#FFFFFF",
            activebackground=PRIMARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=25,
            pady=11,
        )

        save_button.pack(
            side="right",
        )

        save_button.bind(
            "<Enter>",
            lambda event: save_button.configure(
                bg=PRIMARY_HOVER
            ),
        )

        save_button.bind(
            "<Leave>",
            lambda event: save_button.configure(
                bg=PRIMARY
            ),
        )

    # ========================================================
    # UI HELPERS
    # ========================================================

    def _label(
        self,
        parent,
        text,
    ):

        label = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        label.pack(
            fill="x",
            pady=(12, 5),
        )

    def _hint(
        self,
        parent,
        text,
    ):

        label = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 8),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        label.pack(
            fill="x",
            pady=(3, 0),
        )

    def _entry(
        self,
        parent,
    ):

        entry = tk.Entry(
            parent,
            font=("Segoe UI", 10),
            fg=TEXT_PRIMARY,
            bg="#FFFFFF",
            relief="solid",
            bd=1,
        )

        entry.pack(
            fill="x",
            ipady=7,
        )

        return entry

    # ========================================================
    # LOAD SETTINGS
    # ========================================================

    def _load_settings(self):

        db = SessionLocal()

        try:

            settings = (
                db.query(SchoolSettings)
                .order_by(SchoolSettings.id)
                .first()
            )

            # ------------------------------------------------
            # FIRST-TIME CONFIGURATION
            # ------------------------------------------------
            #
            # No SchoolSettings row is a valid state.
            #
            # Do NOT create default values here.
            # Do NOT show an error.
            #
            # The admin must configure the system manually.
            # ------------------------------------------------

            if settings is None:

                self._update_preview()

                return

            # ------------------------------------------------
            # EXISTING CONFIGURATION
            # ------------------------------------------------

            self.school_name_entry.insert(
                0,
                settings.school_name or "",
            )

            self.start_time_entry.insert(
                0,
                settings.attendance_start_time.strftime(
                    "%H:%M"
                ),
            )

            self.end_time_entry.insert(
                0,
                settings.attendance_end_time.strftime(
                    "%H:%M"
                ),
            )

            self.late_entry.insert(
                0,
                str(
                    settings.late_after_minutes
                ),
            )

            self.timezone_entry.insert(
                0,
                settings.timezone or "",
            )

            if settings.report_email:

                self.email_entry.insert(
                    0,
                    settings.report_email,
                )

            self._update_preview()

        except Exception as error:

            messagebox.showerror(
                "Settings Error",
                (
                    "Could not load school settings.\n\n"
                    f"{error}"
                ),
                parent=self.window,
            )

        finally:

            db.close()

    # ========================================================
    # PREVIEW
    # ========================================================

    def _update_preview(self):

        start_text = (
            self.start_time_entry
            .get()
            .strip()
        )

        end_text = (
            self.end_time_entry
            .get()
            .strip()
        )

        try:

            start_time = datetime_to_time(
                start_text
            )

            end_time = datetime_to_time(
                end_text
            )

            self.preview_label.configure(
                text=(
                    f"{start_time.strftime('%H:%M')}"
                    f" - "
                    f"{end_time.strftime('%H:%M')}"
                )
            )

        except Exception:

            self.preview_label.configure(
                text="--:-- - --:--"
            )

    # ========================================================
    # SAVE SETTINGS
    # ========================================================

    def save_settings(self):

        school_name = (
            self.school_name_entry
            .get()
            .strip()
        )

        start_text = (
            self.start_time_entry
            .get()
            .strip()
        )

        end_text = (
            self.end_time_entry
            .get()
            .strip()
        )

        late_text = (
            self.late_entry
            .get()
            .strip()
        )

        timezone = (
            self.timezone_entry
            .get()
            .strip()
        )

        email = (
            self.email_entry
            .get()
            .strip()
        )

        # ----------------------------------------------------
        # SCHOOL NAME VALIDATION
        # ----------------------------------------------------

        if not school_name:

            messagebox.showerror(
                "Invalid Settings",
                "School name cannot be empty.",
                parent=self.window,
            )

            return

        # ----------------------------------------------------
        # START TIME VALIDATION
        # ----------------------------------------------------

        try:

            start_time = datetime_to_time(
                start_text
            )

        except ValueError:

            messagebox.showerror(
                "Invalid Start Time",
                (
                    "Attendance start time is required.\n\n"
                    "Use 24-hour format such as 08:00."
                ),
                parent=self.window,
            )

            return

        # ----------------------------------------------------
        # END TIME VALIDATION
        # ----------------------------------------------------

        try:

            end_time = datetime_to_time(
                end_text
            )

        except ValueError:

            messagebox.showerror(
                "Invalid End Time",
                (
                    "Attendance end time is required.\n\n"
                    "Use 24-hour format such as 10:00."
                ),
                parent=self.window,
            )

            return

        # ----------------------------------------------------
        # ATTENDANCE WINDOW VALIDATION
        # ----------------------------------------------------

        if start_time >= end_time:

            messagebox.showerror(
                "Invalid Attendance Window",
                (
                    "Attendance start time must be earlier "
                    "than attendance end time."
                ),
                parent=self.window,
            )

            return

        # ----------------------------------------------------
        # LATE THRESHOLD VALIDATION
        # ----------------------------------------------------

        try:

            late_after = int(
                late_text
            )

            if late_after < 0:
                raise ValueError

        except ValueError:

            messagebox.showerror(
                "Invalid Late Time",
                (
                    "Late-after minutes are required.\n\n"
                    "Enter a non-negative integer."
                ),
                parent=self.window,
            )

            return

        # ----------------------------------------------------
        # TIMEZONE VALIDATION
        # ----------------------------------------------------

        if not timezone:

            messagebox.showerror(
                "Invalid Timezone",
                "Timezone cannot be empty.",
                parent=self.window,
            )

            return

        # ----------------------------------------------------
        # SAVE TO DATABASE
        # ----------------------------------------------------

        db = SessionLocal()

        try:

            settings = (
                db.query(SchoolSettings)
                .order_by(SchoolSettings.id)
                .first()
            )

            # ------------------------------------------------
            # CREATE FIRST SETTINGS RECORD
            # ------------------------------------------------

            if settings is None:

                settings = SchoolSettings(
                    school_name=school_name,
                    attendance_start_time=start_time,
                    attendance_end_time=end_time,
                    late_after_minutes=late_after,
                    timezone=timezone,
                    report_email=(
                        email
                        if email
                        else None
                    ),
                )

                db.add(settings)

                action_text = (
                    "School attendance settings "
                    "have been configured successfully."
                )

            # ------------------------------------------------
            # UPDATE EXISTING SETTINGS RECORD
            # ------------------------------------------------

            else:

                settings.school_name = school_name

                settings.attendance_start_time = (
                    start_time
                )

                settings.attendance_end_time = (
                    end_time
                )

                settings.late_after_minutes = (
                    late_after
                )

                settings.timezone = timezone

                settings.report_email = (
                    email
                    if email
                    else None
                )

                action_text = (
                    "School attendance settings "
                    "have been updated successfully."
                )

            db.commit()

            messagebox.showinfo(
                "Settings Saved",
                (
                    f"{action_text}\n\n"
                    f"School: {school_name}\n"
                    f"Attendance window: "
                    f"{start_time.strftime('%H:%M')} - "
                    f"{end_time.strftime('%H:%M')}\n"
                    f"Late after: {late_after} minutes\n"
                    f"Timezone: {timezone}"
                ),
                parent=self.window,
            )

            self.window.destroy()

        except Exception as error:

            db.rollback()

            messagebox.showerror(
                "Save Error",
                (
                    "Could not save school settings.\n\n"
                    f"{error}"
                ),
                parent=self.window,
            )

        finally:

            db.close()


# ============================================================
# TIME PARSER
# ============================================================


def datetime_to_time(value):

    parts = value.split(":")

    if len(parts) != 2:
        raise ValueError

    try:

        hour = int(
            parts[0]
        )

        minute = int(
            parts[1]
        )

    except ValueError:

        raise ValueError

    if not 0 <= hour <= 23:
        raise ValueError

    if not 0 <= minute <= 59:
        raise ValueError

    return time(
        hour=hour,
        minute=minute,
    )