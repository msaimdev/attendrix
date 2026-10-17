import ctypes
import tkinter as tk
from tkinter import messagebox

from sqlalchemy import select

from app.auth import verify_password
from app.database import SessionLocal
from app.models import Admin


# ============================================================
# WINDOWS DPI AWARENESS
# ============================================================

def enable_dpi_awareness():
    """
    Tell Windows that this application is DPI-aware.
    Prevents blurry Tkinter rendering on scaled displays.
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

BORDER = "#E2E8F0"


# ============================================================
# LOGIN WINDOW
# ============================================================

class LoginWindow:

    def __init__(self, root, on_success):

        self.root = root
        self.on_success = on_success

        self.root.title("Face Attendance System - Login")
        self.root.geometry("500x430")
        self.root.minsize(450, 400)

        self.root.configure(
            bg=BG_COLOR
        )

        self._build_ui()

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self):

        # ----------------------------------------------------
        # Main container
        # ----------------------------------------------------

        container = tk.Frame(
            self.root,
            bg=BG_COLOR,
        )

        container.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=35,
        )

        # ----------------------------------------------------
        # Card
        # ----------------------------------------------------

        card = tk.Frame(
            container,
            bg=CARD_COLOR,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            fill="both",
            expand=True,
        )

        content = tk.Frame(
            card,
            bg=CARD_COLOR,
        )

        content.pack(
            fill="both",
            expand=True,
            padx=45,
            pady=35,
        )

        # ----------------------------------------------------
        # Logo
        # ----------------------------------------------------

        logo = tk.Frame(
            content,
            bg=PRIMARY,
            width=50,
            height=50,
        )

        logo.pack()

        logo.pack_propagate(False)

        logo_text = tk.Label(
            logo,
            text="FA",
            font=("Segoe UI", 13, "bold"),
            fg="#FFFFFF",
            bg=PRIMARY,
        )

        logo_text.pack(
            expand=True,
        )

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        title = tk.Label(
            content,
            text="Face Attendance",
            font=("Segoe UI", 21, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
        )

        title.pack(
            pady=(18, 3),
        )

        subtitle = tk.Label(
            content,
            text="Administrator Login",
            font=("Segoe UI", 10),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        )

        subtitle.pack(
            pady=(0, 25),
        )

        # ----------------------------------------------------
        # Username
        # ----------------------------------------------------

        username_label = tk.Label(
            content,
            text="Username",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        username_label.pack(
            fill="x",
            pady=(0, 6),
        )

        self.username_entry = tk.Entry(
            content,
            font=("Segoe UI", 10),
            fg=TEXT_PRIMARY,
            bg="#FFFFFF",
            relief="solid",
            bd=1,
        )

        self.username_entry.pack(
            fill="x",
            ipady=8,
        )

        # ----------------------------------------------------
        # Password
        # ----------------------------------------------------

        password_label = tk.Label(
            content,
            text="Password",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_COLOR,
            anchor="w",
        )

        password_label.pack(
            fill="x",
            pady=(16, 6),
        )

        self.password_entry = tk.Entry(
            content,
            font=("Segoe UI", 10),
            fg=TEXT_PRIMARY,
            bg="#FFFFFF",
            relief="solid",
            bd=1,
            show="*",
        )

        self.password_entry.pack(
            fill="x",
            ipady=8,
        )

        # ----------------------------------------------------
        # Login button
        # ----------------------------------------------------

        login_button = tk.Button(
            content,
            text="Login",
            command=self._login,
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=PRIMARY,
            activeforeground="#FFFFFF",
            activebackground=PRIMARY_HOVER,
            relief="flat",
            bd=0,
            cursor="hand2",
            pady=11,
        )

        login_button.pack(
            fill="x",
            pady=(25, 0),
        )

        self._add_hover(
            login_button,
            PRIMARY,
            PRIMARY_HOVER,
        )

        # ----------------------------------------------------
        # Enter key
        # ----------------------------------------------------

        self.username_entry.bind(
            "<Return>",
            lambda event: self._login(),
        )

        self.password_entry.bind(
            "<Return>",
            lambda event: self._login(),
        )

        self.username_entry.focus_set()

    # ========================================================
    # LOGIN
    # ========================================================

    def _login(self):

        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username:

            messagebox.showwarning(
                "Login",
                "Please enter your username.",
                parent=self.root,
            )

            self.username_entry.focus_set()

            return

        if not password:

            messagebox.showwarning(
                "Login",
                "Please enter your password.",
                parent=self.root,
            )

            self.password_entry.focus_set()

            return

        db = SessionLocal()

        try:

            admin = db.scalar(
                select(Admin).where(
                    Admin.username == username,
                    Admin.is_active.is_(True),
                )
            )

            if admin is None:

                messagebox.showerror(
                    "Login Failed",
                    "Invalid username or password.",
                    parent=self.root,
                )

                self.password_entry.delete(
                    0,
                    tk.END,
                )

                self.password_entry.focus_set()

                return

            if not verify_password(
                password,
                admin.password_hash,
            ):

                messagebox.showerror(
                    "Login Failed",
                    "Invalid username or password.",
                    parent=self.root,
                )

                self.password_entry.delete(
                    0,
                    tk.END,
                )

                self.password_entry.focus_set()

                return

            # ------------------------------------------------
            # Authentication successful
            # ------------------------------------------------

            self.root.withdraw()

            self.on_success(admin)

        except Exception as error:

            messagebox.showerror(
                "Login Error",
                (
                    "Unable to complete login.\n\n"
                    f"{error}"
                ),
                parent=self.root,
            )

        finally:

            db.close()

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

    LoginWindow(
        root,
        lambda admin: print(
            f"Logged in as: {admin.username}"
        ),
    )

    root.mainloop()


if __name__ == "__main__":
    main()