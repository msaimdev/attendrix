from getpass import getpass

from sqlalchemy import select

from app.auth import hash_password
from app.database import SessionLocal
from app.models import Admin


def main() -> None:
    print("=" * 60)
    print("Face Attendance System - Create Admin")
    print("=" * 60)

    username = input("Admin username: ").strip()
    full_name = input("Admin full name: ").strip()

    if not username:
        print("ERROR: Username cannot be empty.")
        return

    if not full_name:
        print("ERROR: Full name cannot be empty.")
        return

    password = getpass("Admin password: ")
    confirm_password = getpass("Confirm password: ")

    if not password:
        print("ERROR: Password cannot be empty.")
        return

    if password != confirm_password:
        print("ERROR: Passwords do not match.")
        return

    db = SessionLocal()

    try:
        existing_admin = db.scalar(
            select(Admin).where(
                Admin.username == username
            )
        )

        if existing_admin:
            print(
                f"ERROR: Admin username '{username}' already exists."
            )
            return

        admin = Admin(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print()
        print("ADMIN CREATED SUCCESSFULLY")
        print(f"Username: {admin.username}")
        print(f"Name: {admin.full_name}")
        print(f"Admin ID: {admin.id}")

    except Exception as exc:
        db.rollback()
        print()
        print("ERROR: Could not create admin.")
        print(exc)

    finally:
        db.close()


if __name__ == "__main__":
    main()