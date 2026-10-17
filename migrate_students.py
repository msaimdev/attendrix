import json
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Student


# ============================================================
# CONFIGURATION
# ============================================================

STUDENTS_DIRECTORY = Path("data/students")


# ============================================================
# MIGRATION
# ============================================================


def migrate_students():
    if not STUDENTS_DIRECTORY.exists():
        print("ERROR: data/students directory does not exist.")
        return

    json_files = sorted(
        STUDENTS_DIRECTORY.glob("*.json")
    )

    print(
        f"Found {len(json_files)} JSON student file(s)."
    )

    if not json_files:
        print("Nothing to migrate.")
        return

    db = SessionLocal()

    migrated = 0
    skipped = 0
    failed = 0

    try:
        for path in json_files:
            print()
            print(f"Processing: {path.name}")

            try:
                with open(
                    path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    data = json.load(file)

                # ------------------------------------------------
                # Validate required fields
                # ------------------------------------------------

                required_fields = [
                    "student_id",
                    "name",
                    "class",
                    "features",
                ]

                missing_fields = [
                    field
                    for field in required_fields
                    if field not in data
                ]

                if missing_fields:
                    print(
                        "  FAILED: missing fields:",
                        missing_fields,
                    )
                    failed += 1
                    continue

                student_id = data["student_id"]

                # ------------------------------------------------
                # Check whether already migrated
                # ------------------------------------------------

                existing = db.scalar(
                    select(Student).where(
                        Student.id == student_id
                    )
                )

                if existing is not None:
                    print(
                        "  SKIPPED: student already exists "
                        "in database."
                    )
                    skipped += 1
                    continue

                # ------------------------------------------------
                # Create database record
                # ------------------------------------------------

                student = Student(
                    id=student_id,
                    name=data["name"],
                    student_class=data["class"],
                    face_features=data["features"],
                    is_active=True,
                )

                db.add(student)

                # ------------------------------------------------
                # Flush so database constraints are checked
                # ------------------------------------------------

                db.flush()

                print(
                    f"  MIGRATED: "
                    f"{data['name']} | "
                    f"{data['class']} | "
                    f"{student_id}"
                )

                migrated += 1

            except Exception as exc:
                db.rollback()

                print(
                    f"  FAILED: {exc}"
                )

                failed += 1

        # --------------------------------------------------------
        # Commit all successful migrations
        # --------------------------------------------------------

        db.commit()

        print()
        print("=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"Migrated : {migrated}")
        print(f"Skipped  : {skipped}")
        print(f"Failed   : {failed}")
        print("=" * 60)

    finally:
        db.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    migrate_students()