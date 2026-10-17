import ctypes
import tkinter as tk
from tkinter import messagebox

from app.attendance_session import AttendanceSession
from app.ui.student_window import StudentWindow
from app.ui.report_window import ReportWindow
from app.ui.settings_window import SettingsWindow


# ============================================================
# WINDOWS DPI AWARENESS
# ============================================================

def enable_dpi_awareness():
    """
    Tell Windows that this application is DPI-aware.
    This helps keep Tkinter text and controls sharp.
    """
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


enable_dpi_awareness()


# ============================================================
# COLORS
# ============================================================

BG_COLOR = "#F5F8FC"

# Sidebar
SIDEBAR_COLOR = "#1E40AF"
SIDEBAR_DARK = "#1E3A8A"
SIDEBAR_TEXT = "#FFFFFF"
SIDEBAR_MUTED = "#DCE7FF"

# Main content
CARD_COLOR = "#FFFFFF"

TEXT_PRIMARY = "#172033"
TEXT_SECONDARY = "#64748B"

# Primary action
PRIMARY = "#3B82F6"
PRIMARY_HOVER = "#2563EB"

# Secondary buttons
SECONDARY = "#EEF3FA"
SECONDARY_HOVER = "#E2EAF5"

BORDER = "#E2E8F0"


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow:

    def __init__(self, root):
        self.root = root

        self.root.title("Face Attendance System")
        self.root.geometry("1100x700")
        self.root.minsize(1000, 650)

        self.root.configure(bg=BG_COLOR)

        self._build_ui()

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self):

        main = tk.Frame(
            self.root,
            bg=BG_COLOR,
        )

        main.pack(
            fill="both",
            expand=True,
        )

        # ----------------------------------------------------
        # LEFT SIDEBAR
        # ----------------------------------------------------

        sidebar = tk.Frame(
            main,
            bg=SIDEBAR_COLOR,
            width=245,
        )

        sidebar.pack(
            side="left",
            fill="y",
        )

        sidebar.pack_propagate(False)

        self._build_sidebar(sidebar)

        # ----------------------------------------------------
        # RIGHT CONTENT
        # ----------------------------------------------------

        content_area = tk.Frame(
            main,
            bg=BG_COLOR,
        )

        content_area.pack(
            side="left",
            fill="both",
            expand=True,
        )

        self._build_content(content_area)

    # ========================================================
    # SIDEBAR
    # ========================================================

    def _build_sidebar(self, sidebar):

        # ----------------------------------------------------
        # Logo
        # ----------------------------------------------------

        logo_container = tk.Frame(
            sidebar,
            bg=SIDEBAR_COLOR,
        )

        logo_container.pack(
            fill="x",
            padx=24,
            pady=(32, 40),
        )

        logo = tk.Frame(
            logo_container,
            bg="#FFFFFF",
            width=42,
            height=42,
        )

        logo.pack(
            anchor="w",
        )

        logo.pack_propagate(False)

        logo_text = tk.Label(
            logo,
            text="FA",
            font=("Segoe UI", 12, "bold"),
            fg=SIDEBAR_COLOR,
            bg="#FFFFFF",
        )

        logo_text.pack(
            expand=True,
        )

        app_name = tk.Label(
            logo_container,
            text="Face Attendance",
            font=("Segoe UI", 15, "bold"),
            fg=SIDEBAR_TEXT,
            bg=SIDEBAR_COLOR,
            anchor="w",
        )

        app_name.pack(
            fill="x",
            pady=(14, 0),
        )

        app_subtitle = tk.Label(
            logo_container,
            text="School Management",
            font=("Segoe UI", 9),
            fg=SIDEBAR_MUTED,
            bg=SIDEBAR_COLOR,
            anchor="w",
        )

        app_subtitle.pack(
            fill="x",
            pady=(3, 0),
        )

        # ----------------------------------------------------
        # Navigation title
        # ----------------------------------------------------

        nav_title = tk.Label(
            sidebar,
            text="MENU",
            font=("Segoe UI", 8, "bold"),
            fg=SIDEBAR_MUTED,
            bg=SIDEBAR_COLOR,
            anchor="w",
        )

        nav_title.pack(
            fill="x",
            padx=24,
            pady=(0, 12),
        )

        # ----------------------------------------------------
        # Navigation buttons
        # ----------------------------------------------------

        self._sidebar_button(
            sidebar,
            text="Dashboard",
            command=self.show_dashboard,
            active=True,
        )

        self._sidebar_button(
            sidebar,
            text="Students",
            command=self.manage_students,
        )

        self._sidebar_button(
            sidebar,
            text="Attendance",
            command=self.start_attendance,
        )

        self._sidebar_button(
            sidebar,
            text="Reports",
            command=self.view_reports,
        )

        self._sidebar_button(
            sidebar,
            text="Settings",
            command=self.open_settings,
        )

        # ----------------------------------------------------
        # Bottom section
        # ----------------------------------------------------

        bottom = tk.Frame(
            sidebar,
            bg=SIDEBAR_COLOR,
        )

        bottom.pack(
            side="bottom",
            fill="x",
            padx=24,
            pady=24,
        )

        separator = tk.Frame(
            bottom,
            bg="#3155B8",
            height=1,
        )

        separator.pack(
            fill="x",
            pady=(0, 18),
        )

        system_label = tk.Label(
            bottom,
            text="Attendance System",
            font=("Segoe UI", 9, "bold"),
            fg=SIDEBAR_TEXT,
            bg=SIDEBAR_COLOR,
            anchor="w",
        )

        system_label.pack(
            fill="x",
        )

        version_label = tk.Label(
            bottom,
            text="School Edition",
            font=("Segoe UI", 8),
            fg=SIDEBAR_MUTED,
            bg=SIDEBAR_COLOR,
            anchor="w",
        )

        version_label.pack(
            fill="x",
            pady=(3, 0),
        )

    # ========================================================
    # SIDEBAR BUTTON
    # ========================================================

    def _sidebar_button(
        self,
        parent,
        text,
        command,
        active=False,
    ):

        normal_bg = (
            SIDEBAR_DARK
            if active
            else SIDEBAR_COLOR
        )

        hover_bg = (
            "#29499C"
            if active
            else "#3155B8"
        )

        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 10, "bold"),
            fg=SIDEBAR_TEXT,
            bg=normal_bg,
            activeforeground=SIDEBAR_TEXT,
            activebackground=hover_bg,
            relief="flat",
            bd=0,
            cursor="hand2",
            anchor="w",
            padx=24,
            pady=11,
        )

        button.pack(
            fill="x",
            padx=12,
            pady=3,
        )

        button.bind(
            "<Enter>",
            lambda event: button.configure(
                bg=hover_bg
            ),
        )

        button.bind(
            "<Leave>",
            lambda event: button.configure(
                bg=normal_bg
            ),
        )

    # ========================================================
    # MAIN CONTENT
    # ========================================================

    def _build_content(self, parent):

        self.content_parent = parent

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header = tk.Frame(
            parent,
            bg=BG_COLOR,
        )

        header.pack(
            fill="x",
            padx=48,
            pady=(40, 28),
        )

        title = tk.Label(
            header,
            text="Dashboard",
            font=("Segoe UI", 25, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_COLOR,
            anchor="w",
        )

        title.pack(
            fill="x",
        )

        subtitle = tk.Label(
            header,
            text="Manage student attendance from one place.",
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
        # Main card
        # ----------------------------------------------------

        card = tk.Frame(
            parent,
            bg=CARD_COLOR,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            fill="both",
            expand=True,
            padx=48,
            pady=(0, 40),
        )

        # ----------------------------------------------------
        # Card content
        # ----------------------------------------------------

        card_content = tk.Frame(
            card,
            bg=CARD_COLOR,
        )

        card_content.pack(
            fill="both",
            expand=True,
            padx=45,
            pady=42,
        )

        # ----------------------------------------------------
        # Welcome
        # ----------------------------------------------------

        welcome = tk.Label(
            card_content,
            text="Welcome back",
            font=("Segoe UI", 20, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        welcome.pack(
            fill="x",
        )

        description = tk.Label(
            card_content,
            text=(
                "Choose an action below to manage "
                "your school's attendance."
            ),
            font=("Segoe UI", 10),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        description.pack(
            fill="x",
            pady=(7, 30),
        )

        # ----------------------------------------------------
        # Start attendance
        # ----------------------------------------------------

        start_button = tk.Button(
            card_content,
            text="Start Attendance",
            command=self.start_attendance,
            font=("Segoe UI", 11, "bold"),
            fg="#FFFFFF",
            bg=PRIMARY,
            activeforeground="#FFFFFF",
            activebackground=PRIMARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=14,
        )

        start_button.pack(
            fill="x",
            pady=(0, 12),
        )

        self._add_hover(
            start_button,
            PRIMARY,
            PRIMARY_HOVER,
        )

        # ----------------------------------------------------
        # Manage students
        # ----------------------------------------------------

        students_button = tk.Button(
            card_content,
            text="Manage Students",
            command=self.manage_students,
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_PRIMARY,
            bg=SECONDARY,
            activeforeground=TEXT_PRIMARY,
            activebackground=SECONDARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=14,
        )

        students_button.pack(
            fill="x",
            pady=(0, 12),
        )

        self._add_hover(
            students_button,
            SECONDARY,
            SECONDARY_HOVER,
        )

        # ----------------------------------------------------
        # Reports
        # ----------------------------------------------------

        reports_button = tk.Button(
            card_content,
            text="Attendance Reports",
            command=self.view_reports,
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_PRIMARY,
            bg=SECONDARY,
            activeforeground=TEXT_PRIMARY,
            activebackground=SECONDARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=14,
        )

        reports_button.pack(
            fill="x",
            pady=(0, 12),
        )

        self._add_hover(
            reports_button,
            SECONDARY,
            SECONDARY_HOVER,
        )

        # ----------------------------------------------------
        # Settings
        # ----------------------------------------------------

        settings_button = tk.Button(
            card_content,
            text="School Settings",
            command=self.open_settings,
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_PRIMARY,
            bg=SECONDARY,
            activeforeground=TEXT_PRIMARY,
            activebackground=SECONDARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=14,
        )

        settings_button.pack(
            fill="x",
        )

        self._add_hover(
            settings_button,
            SECONDARY,
            SECONDARY_HOVER,
        )

        # ----------------------------------------------------
        # Footer
        # ----------------------------------------------------

        footer = tk.Label(
            parent,
            text="Face Attendance System • School Edition",
            font=("Segoe UI", 8),
            fg=TEXT_SECONDARY,
            bg=BG_COLOR,
        )

        footer.pack(
            side="bottom",
            pady=(0, 15),
        )

    # ========================================================
    # HOVER EFFECT
    # ========================================================

    @staticmethod
    def _add_hover(
        button,
        normal_color,
        hover_color,
    ):

        button.bind(
            "<Enter>",
            lambda event: button.configure(
                bg=hover_color
            ),
        )

        button.bind(
            "<Leave>",
            lambda event: button.configure(
                bg=normal_color
            ),
        )

    # ========================================================
    # DASHBOARD
    # ========================================================

    def show_dashboard(self):
        """
        Dashboard is already the main screen.
        """
        pass

    # ========================================================
    # START ATTENDANCE
    # ========================================================

    def start_attendance(self):
        """
        Start the real live attendance session.
        """

        try:
            session = AttendanceSession(
                camera_index=0,
                preview_window=True,
                confirmation_frames=5,
                required_matches=3,
                departure_frames=10,
            )

            session.start()

        except Exception as error:
            messagebox.showerror(
                "Attendance Error",
                (
                    "Could not start attendance session.\n\n"
                    f"{error}"
                ),
                parent=self.root,
            )

    # ========================================================
    # MANAGE STUDENTS
    # ========================================================

    def manage_students(self):
        """
        Open the administrator student-management window.
        """

        try:
            StudentWindow(self.root)

        except Exception as error:
            messagebox.showerror(
                "Student Management Error",
                (
                    "Could not open student management.\n\n"
                    f"{error}"
                ),
                parent=self.root,
            )

    # ========================================================
    # ATTENDANCE REPORTS
    # ========================================================

    def view_reports(self):
        """
        Open the attendance reports window.
        """

        try:
            ReportWindow(self.root)

        except Exception as error:
            messagebox.showerror(
                "Reports Error",
                (
                    "Could not open attendance reports.\n\n"
                    f"{error}"
                ),
                parent=self.root,
            )

    # ========================================================
    # SCHOOL SETTINGS
    # ========================================================

    def open_settings(self):
        """
        Open the school settings window.

        This is where the administrator will be able to
        configure school-specific settings such as:

        - School name
        - Attendance start time
        - Attendance end time
        - Late threshold
        - Timezone
        - Report email
        - Other configurable school settings
        """

        try:
            SettingsWindow(self.root)

        except Exception as error:
            messagebox.showerror(
                "Settings Error",
                (
                    "Could not open school settings.\n\n"
                    f"{error}"
                ),
                parent=self.root,
            )


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

def main():

    root = tk.Tk()

    MainWindow(root)

    root.mainloop()


if __name__ == "__main__":
    main()
