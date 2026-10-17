import ctypes
import tkinter as tk
from tkinter import messagebox


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


from app.student import StudentManager


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

DANGER = "#DC2626"
DANGER_HOVER = "#B91C1C"


# ============================================================
# STUDENT WINDOW
# ============================================================

class StudentWindow:

    def __init__(self, parent):

        self.parent = parent
        self.manager = StudentManager()

        self.window = tk.Toplevel(parent)

        self.window.title("Manage Students")
        self.window.geometry("1000x650")
        self.window.minsize(900, 600)

        self.window.configure(bg=BG_COLOR)

        self._build_ui()

        self._load_students()

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
            padx=45,
            pady=(35, 25),
        )

        title = tk.Label(
            header,
            text="Manage Students",
            font=("Segoe UI", 24, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_COLOR,
            anchor="w",
        )

        title.pack(
            fill="x",
        )

        subtitle = tk.Label(
            header,
            text="View and manage registered students.",
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
            self.window,
            bg=CARD_COLOR,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            fill="both",
            expand=True,
            padx=45,
            pady=(0, 35),
        )

        # ----------------------------------------------------
        # Card header
        # ----------------------------------------------------

        card_header = tk.Frame(
            card,
            bg=CARD_COLOR,
        )

        card_header.pack(
            fill="x",
            padx=30,
            pady=(25, 20),
        )

        # ----------------------------------------------------
        # Left side of card header
        # ----------------------------------------------------

        header_left = tk.Frame(
            card_header,
            bg=CARD_COLOR,
        )

        header_left.pack(
            side="left",
            fill="x",
            expand=True,
        )

        students_label = tk.Label(
            header_left,
            text="Registered Students",
            font=("Segoe UI", 15, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        students_label.pack(
            side="left",
        )

        self.count_label = tk.Label(
            header_left,
            text="0 students",
            font=("Segoe UI", 9),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        )

        self.count_label.pack(
            side="left",
            padx=(14, 0),
        )

        # ----------------------------------------------------
        # Add Student button
        # ----------------------------------------------------

        add_button = tk.Button(
            card_header,
            text="+ Add Student",
            command=self._add_student,
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

        add_button.pack(
            side="right",
        )

        self._add_hover(
            add_button,
            PRIMARY,
            PRIMARY_HOVER,
        )

        # ----------------------------------------------------
        # Table area
        # ----------------------------------------------------

        table_container = tk.Frame(
            card,
            bg=CARD_COLOR,
        )

        table_container.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 20),
        )

        # ----------------------------------------------------
        # Table header
        # ----------------------------------------------------

        table_header = tk.Frame(
            table_container,
            bg=SECONDARY,
            height=42,
        )

        table_header.pack(
            fill="x",
        )

        table_header.pack_propagate(False)

        # No Student ID column.
        # UUID remains in the database and is used internally.

        self._table_header(
            table_header,
            "Name",
            0,
        )

        self._table_header(
            table_header,
            "Class",
            1,
        )

        self._table_header(
            table_header,
            "Action",
            2,
        )

        # ----------------------------------------------------
        # Scrollable student list
        # ----------------------------------------------------

        self.canvas = tk.Canvas(
            table_container,
            bg=CARD_COLOR,
            highlightthickness=0,
            bd=0,
        )

        scrollbar = tk.Scrollbar(
            table_container,
            orient="vertical",
            command=self.canvas.yview,
        )

        self.student_frame = tk.Frame(
            self.canvas,
            bg=CARD_COLOR,
        )

        self.student_frame.bind(
            "<Configure>",
            lambda event: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.student_frame,
            anchor="nw",
        )

        self.canvas.configure(
            yscrollcommand=scrollbar.set,
        )

        self.canvas.bind(
            "<Configure>",
            self._resize_student_frame,
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        # ----------------------------------------------------
        # Bottom buttons
        # ----------------------------------------------------

        bottom = tk.Frame(
            card,
            bg=CARD_COLOR,
        )

        bottom.pack(
            fill="x",
            padx=30,
            pady=(0, 25),
        )

        refresh_button = tk.Button(
            bottom,
            text="Refresh",
            command=self._load_students,
            font=("Segoe UI", 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=SECONDARY,
            activeforeground=TEXT_PRIMARY,
            activebackground=SECONDARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=22,
            pady=10,
        )

        refresh_button.pack(
            side="left",
        )

        self._add_hover(
            refresh_button,
            SECONDARY,
            SECONDARY_HOVER,
        )

        close_button = tk.Button(
            bottom,
            text="Close",
            command=self.window.destroy,
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=PRIMARY,
            activeforeground="#FFFFFF",
            activebackground=PRIMARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=22,
            pady=10,
        )

        close_button.pack(
            side="right",
        )

        self._add_hover(
            close_button,
            PRIMARY,
            PRIMARY_HOVER,
        )

    # ========================================================
    # TABLE HEADER
    # ========================================================

    @staticmethod
    def _table_header(parent, text, column):

        widths = {
            0: 55,
            1: 20,
            2: 25,
        }

        start = sum(
            widths[i]
            for i in range(column)
        )

        label = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=SECONDARY,
            anchor="w",
        )

        label.place(
            relx=start / 100,
            rely=0,
            relwidth=widths[column] / 100,
            relheight=1,
        )

    # ========================================================
    # RESIZE TABLE
    # ========================================================

    def _resize_student_frame(self, event):

        self.canvas.itemconfig(
            self.canvas_window,
            width=event.width,
        )

    # ========================================================
    # LOAD STUDENTS
    # ========================================================

    def _load_students(self):

        for widget in self.student_frame.winfo_children():
            widget.destroy()

        try:
            students = self.manager.get_all_students()

        except Exception as error:

            messagebox.showerror(
                "Error",
                f"Unable to load students.\n\n{error}",
                parent=self.window,
            )

            return

        self.count_label.configure(
            text=(
                f"{len(students)} "
                f"student{'s' if len(students) != 1 else ''}"
            )
        )

        if not students:

            empty_label = tk.Label(
                self.student_frame,
                text="No students registered.",
                font=("Segoe UI", 10),
                fg=TEXT_SECONDARY,
                bg=CARD_COLOR,
            )

            empty_label.pack(
                pady=40,
            )

            return

        for student in students:
            self._add_student_row(student)

    # ========================================================
    # STUDENT ROW
    # ========================================================

    def _add_student_row(self, student):

        row = tk.Frame(
            self.student_frame,
            bg=CARD_COLOR,
            height=58,
        )

        row.pack(
            fill="x",
        )

        row.pack_propagate(False)

        # ----------------------------------------------------
        # Name
        # ----------------------------------------------------

        name_label = tk.Label(
            row,
            text=student["name"],
            font=("Segoe UI", 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        name_label.place(
            relx=0,
            rely=0,
            relwidth=0.55,
            relheight=1,
        )

        # ----------------------------------------------------
        # Class
        # ----------------------------------------------------

        class_label = tk.Label(
            row,
            text=student["class"],
            font=("Segoe UI", 10),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        class_label.place(
            relx=0.55,
            rely=0,
            relwidth=0.20,
            relheight=1,
        )

        # ----------------------------------------------------
        # Deactivate button
        # ----------------------------------------------------

        delete_button = tk.Button(
            row,
            text="Deactivate",
            command=lambda sid=student["student_id"]: (
                self._deactivate_student(sid)
            ),
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg=DANGER,
            activeforeground="#FFFFFF",
            activebackground=DANGER_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=6,
        )

        delete_button.place(
            relx=0.78,
            rely=0.5,
            anchor="w",
        )

        self._add_hover(
            delete_button,
            DANGER,
            DANGER_HOVER,
        )

        # ----------------------------------------------------
        # Separator
        # ----------------------------------------------------

        separator = tk.Frame(
            row,
            bg=BORDER,
            height=1,
        )

        separator.pack(
            side="bottom",
            fill="x",
        )

    # ========================================================
    # ADD STUDENT
    # ========================================================

    def _add_student(self):

        messagebox.showinfo(
            "Add Student",
            "Student registration will open here.",
            parent=self.window,
        )

    # ========================================================
    # DEACTIVATE STUDENT
    # ========================================================

    def _deactivate_student(self, student_id):

        confirm = messagebox.askyesno(
            "Deactivate Student",
            (
                "Are you sure you want to deactivate "
                "this student?\n\n"
                "Their historical attendance records "
                "will be preserved."
            ),
            parent=self.window,
        )

        if not confirm:
            return

        try:

            success = self.manager.delete_student(
                student_id
            )

            if not success:

                messagebox.showwarning(
                    "Student Not Found",
                    "The student could not be found.",
                    parent=self.window,
                )

                return

            messagebox.showinfo(
                "Student Deactivated",
                "The student has been deactivated.",
                parent=self.window,
            )

            self._load_students()

        except Exception as error:

            messagebox.showerror(
                "Error",
                (
                    "Unable to deactivate the student.\n\n"
                    f"{error}"
                ),
                parent=self.window,
            )

    # ========================================================
    # HOVER
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
# STANDALONE TEST
# ============================================================

def main():

    root = tk.Tk()

    root.withdraw()

    StudentWindow(root)

    root.mainloop()


if __name__ == "__main__":
    main()