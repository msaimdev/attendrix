import tkinter as tk

from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


class FaceAttendanceApp:
    """
    Main desktop application entry point.

    Application flow:

        LoginWindow
             ↓
        successful authentication
             ↓
        MainWindow
    """

    def __init__(self):
        self.root = tk.Tk()

        self.main_window = None

        LoginWindow(
            self.root,
            self.on_login_success,
        )

    def on_login_success(self, admin):
        """
        Open the main dashboard after successful login.
        """

        self.main_window = MainWindow(
            self.root
        )

    def run(self):
        """
        Start the Tkinter event loop.
        """

        self.root.mainloop()


def main():
    app = FaceAttendanceApp()
    app.run()


if __name__ == "__main__":
    main()