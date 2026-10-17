import ctypes
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from app.attendance import AttendanceManager


# ============================================================
# WINDOWS DPI AWARENESS
# ============================================================

def enable_dpi_awareness():
    """
    Tell Windows that this application is DPI-aware.
    This helps prevent blurry Tkinter rendering.
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
CARD_COLOR = "#FFFFFF"

TEXT_PRIMARY = "#172033"
TEXT_SECONDARY = "#64748B"

PRIMARY = "#3B82F6"
PRIMARY_HOVER = "#2563EB"

SECONDARY = "#EEF3FA"
SECONDARY_HOVER = "#E2EAF5"

BORDER = "#E2E8F0"

SUCCESS = "#16A34A"
DANGER = "#DC2626"


# ============================================================
# REPORT WINDOW
# ============================================================

class ReportWindow:

    def __init__(self, parent=None):
        self.parent = parent

        self.window = tk.Toplevel(parent) if parent else tk.Tk()

        self.window.title("Attendance Reports")
        self.window.geometry("1100x700")
        self.window.minsize(1000, 650)

        self.window.configure(bg=BG_COLOR)

        if parent:
            self.window.transient(parent)

        self.attendance_manager = AttendanceManager()

        self._build_ui()

        self.load_report()

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self):

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header = tk.Frame(
            self.window,
            bg=BG_COLOR,
        )

        header.pack(
            fill="x",
            padx=48,
            pady=(40, 25),
        )

        title = tk.Label(
            header,
            text="Attendance Reports",
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
            text="View attendance records and daily summaries.",
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
        # Controls
        # ----------------------------------------------------

        controls = tk.Frame(
            self.window,
            bg=BG_COLOR,
        )

        controls.pack(
            fill="x",
            padx=48,
            pady=(0, 20),
        )

        date_label = tk.Label(
            controls,
            text="Date",
            font=("Segoe UI", 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_COLOR,
        )

        date_label.pack(
            side="left",
        )

        self.date_entry = tk.Entry(
            controls,
            font=("Segoe UI", 10),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            relief="solid",
            bd=1,
            width=14,
        )

        self.date_entry.pack(
            side="left",
            padx=(10, 10),
            ipady=7,
        )

        self.date_entry.insert(
            0,
            date.today().isoformat(),
        )

        refresh_button = tk.Button(
            controls,
            text="Load Report",
            command=self.load_report,
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=PRIMARY,
            activeforeground="#FFFFFF",
            activebackground=PRIMARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18,
            pady=9,
        )

        refresh_button.pack(
            side="left",
        )

        self._add_hover(
            refresh_button,
            PRIMARY,
            PRIMARY_HOVER,
        )

        # ----------------------------------------------------
        # Summary cards
        # ----------------------------------------------------

        summary = tk.Frame(
            self.window,
            bg=BG_COLOR,
        )

        summary.pack(
            fill="x",
            padx=48,
            pady=(0, 20),
        )

        self.total_value = self._summary_card(
            summary,
            "Total Students",
            "0",
        )

        self.present_value = self._summary_card(
            summary,
            "Present",
            "0",
        )

        self.absent_value = self._summary_card(
            summary,
            "Absent",
            "0",
        )

        self.percentage_value = self._summary_card(
            summary,
            "Attendance",
            "0%",
        )

        # ----------------------------------------------------
        # Attendance table card
        # ----------------------------------------------------

        table_card = tk.Frame(
            self.window,
            bg=CARD_COLOR,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        table_card.pack(
            fill="both",
            expand=True,
            padx=48,
            pady=(0, 35),
        )

        table_container = tk.Frame(
            table_card,
            bg=CARD_COLOR,
        )

        table_container.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=25,
        )

        # ----------------------------------------------------
        # Table title
        # ----------------------------------------------------

        table_title = tk.Label(
            table_container,
            text="Daily Attendance",
            font=("Segoe UI", 15, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        table_title.pack(
            fill="x",
            pady=(0, 15),
        )

        # ----------------------------------------------------
        # Treeview styling
        # ----------------------------------------------------

        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Attendance.Treeview",
            background=CARD_COLOR,
            foreground=TEXT_PRIMARY,
            fieldbackground=CARD_COLOR,
            rowheight=38,
            font=("Segoe UI", 10),
            borderwidth=0,
        )

        style.configure(
            "Attendance.Treeview.Heading",
            background=SECONDARY,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=10,
        )

        style.map(
            "Attendance.Treeview",
            background=[
                ("selected", "#DBEAFE"),
            ],
            foreground=[
                ("selected", TEXT_PRIMARY),
            ],
        )

        # ----------------------------------------------------
        # Table
        # ----------------------------------------------------

        table_frame = tk.Frame(
            table_container,
            bg=CARD_COLOR,
        )

        table_frame.pack(
            fill="both",
            expand=True,
        )

        columns = (
            "name",
            "class",
            "status",
            "time",
        )

        self.table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Attendance.Treeview",
        )

        self.table.heading(
            "name",
            text="Name",
        )

        self.table.heading(
            "class",
            text="Class",
        )

        self.table.heading(
            "status",
            text="Status",
        )

        self.table.heading(
            "time",
            text="Time",
        )

        self.table.column(
            "name",
            width=300,
            anchor="w",
        )

        self.table.column(
            "class",
            width=160,
            anchor="center",
        )

        self.table.column(
            "status",
            width=160,
            anchor="center",
        )

        self.table.column(
            "time",
            width=180,
            anchor="center",
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.table.yview,
        )

        self.table.configure(
            yscrollcommand=scrollbar.set,
        )

        self.table.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

    # ========================================================
    # SUMMARY CARD
    # ========================================================

    def _summary_card(
        self,
        parent,
        title,
        value,
    ):

        card = tk.Frame(
            parent,
            bg=CARD_COLOR,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 12),
        )

        label = tk.Label(
            card,
            text=title,
            font=("Segoe UI", 9),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        )

        label.pack(
            anchor="w",
            padx=18,
            pady=(14, 3),
        )

        value_label = tk.Label(
            card,
            text=value,
            font=("Segoe UI", 18, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
        )

        value_label.pack(
            anchor="w",
            padx=18,
            pady=(0, 14),
        )

        return value_label

    # ========================================================
    # LOAD REPORT
    # ========================================================

    def load_report(self):

        date_text = self.date_entry.get().strip()

        try:
            selected_date = date.fromisoformat(
                date_text
            )
        except ValueError:

            messagebox.showerror(
                "Invalid Date",
                "Please enter the date in YYYY-MM-DD format.",
                parent=self.window,
            )

            return

        try:
            report = self.attendance_manager.generate_report(
                selected_date
            )

            records = self.attendance_manager.load_daily_attendance(
                selected_date
            )

        except Exception as error:

            messagebox.showerror(
                "Report Error",
                f"Unable to load attendance report.\n\n{error}",
                parent=self.window,
            )

            return

        # ----------------------------------------------------
        # Update summary
        # ----------------------------------------------------

        self.total_value.configure(
            text=str(
                report["total_students"]
            )
        )

        self.present_value.configure(
            text=str(
                report["present"]
            )
        )

        self.absent_value.configure(
            text=str(
                report["absent"]
            )
        )

        self.percentage_value.configure(
            text=f'{report["attendance_percentage"]}%'
        )

        # ----------------------------------------------------
        # Clear existing table
        # ----------------------------------------------------

        for item in self.table.get_children():
            self.table.delete(item)

        # ----------------------------------------------------
        # Add attendance records
        # ----------------------------------------------------

        for record in records:

            self.table.insert(
                "",
                "end",
                values=(
                    record["student_name"],
                    record["class"],
                    record["status"],
                    record["time"] or "-",
                ),
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


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

def main():

    root = tk.Tk()

    ReportWindow(root)

    root.mainloop()


if __name__ == "__main__":
    main()