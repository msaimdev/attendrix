from pathlib import Path
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.db_guard import verify_sqlite_file


# ============================================================
# DATABASE PATH
# ============================================================

DATABASE_DIRECTORY = Path("data")

DATABASE_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


# Production remains the default.
# Tests can explicitly override this with TEST_DATABASE_URL.
DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///" + str(DATABASE_DIRECTORY / "attendance.db"),
)

# Only protect/validate the real production database here.
if "TEST_DATABASE_URL" not in os.environ:
    DATABASE_PATH = DATABASE_DIRECTORY / "attendance.db"
    verify_sqlite_file(DATABASE_PATH)
else:
    DATABASE_PATH = None


# ============================================================
# DATABASE ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
)


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    """
    Provide a database session for a request.

    The session is always closed after the request
    finishes, even if an error occurs.
    """
    db: Session = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# BASE MODEL
# ============================================================


class Base(DeclarativeBase):
    pass
