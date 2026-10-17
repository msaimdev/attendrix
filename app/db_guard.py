from pathlib import Path

SQLITE_MAGIC = b"SQLite format 3\x00"


def verify_sqlite_file(db_path):
    """
    Raise a clear, loud error if db_path is not a valid SQLite database file.
    Call this at application startup, before any DB engine/session is created.
    """
    path = Path(db_path)

    if not path.exists():
        # Fine - a fresh DB will be created by migrations. Not an error.
        return

    # Read only the header, not the whole database — this runs
    # at startup and the file grows for the life of the school.
    with path.open("rb") as db_file:
        header = db_file.read(16)

    if header != SQLITE_MAGIC:
        raise RuntimeError(
            "\n\nFATAL: '" + str(path) + "' is not a valid SQLite database file.\n"
            "Expected header: " + repr(SQLITE_MAGIC) + "\n"
            "Found header:    " + repr(header) + "\n\n"
            "This usually means the file was accidentally overwritten "
            "(e.g. a PowerShell '>' or '2>' redirect pointed at this path).\n"
            "DO NOT delete this file - it may contain diagnostic clues.\n"
            "Restore from a known-good backup or run 'alembic upgrade head' "
            "against a fresh path instead.\n"
        )
