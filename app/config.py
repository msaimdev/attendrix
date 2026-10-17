from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Face Attendance System"
    app_version: str = "1.0.0"

    # ========================================================
    # APPLICATION SECURITY
    # ========================================================

    session_secret: str

    # ========================================================
    # SERVER / NETWORK
    # ========================================================

    # Interface the web server binds to.
    #
    # "127.0.0.1" -> reachable only from this machine.
    # "0.0.0.0"   -> reachable from any device on the school
    #                network (needed so staff can open the
    #                dashboard from their own computers).
    #
    # Binding to 0.0.0.0 exposes the login page to everyone on
    # the LAN, so the admin password is the only thing keeping
    # them out. Keep it strong, and keep this machine off
    # untrusted/public Wi-Fi.
    server_host: str = "127.0.0.1"
    server_port: int = 8000

    # ========================================================
    # SMTP / EMAIL
    # ========================================================

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from: str

    # ========================================================
    # CAMERAS
    # ========================================================

    # The camera physically mounted at the school entrance,
    # used by the automatic attendance scheduler.
    attendance_camera_index: str = "0"

    # The camera used by the admin when registering new
    # students (e.g. a second webcam at the admin's desk).
    # Defaults to a different index than the attendance
    # camera so the two don't fight over the same device.
    registration_camera_index: str = "0"

    # Show the live OpenCV preview window during an attendance
    # session.
    #
    # Only safe when the session runs on the main thread (the
    # legacy desktop app). The web server runs the session on
    # a background thread, where OpenCV's window code is not
    # thread-safe and can hang or crash the process, so this
    # stays off by default.
    attendance_preview_window: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()