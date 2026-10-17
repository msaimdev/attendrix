from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin


# ============================================================
# PASSWORD HASHING
# ============================================================

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using the recommended
    password hashing algorithm.
    """
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against its stored hash.
    """
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

def authenticate_admin(
    db: Session,
    username: str,
    password: str,
) -> Admin | None:
    """
    Authenticate an admin using username and password.

    Returns the active Admin if credentials are valid.
    Returns None if authentication fails.
    """

    admin = db.scalar(
        select(Admin).where(
            Admin.username == username,
            Admin.is_active.is_(True),
        )
    )

    if admin is None:
        return None

    if not verify_password(
        password,
        admin.password_hash,
    ):
        return None

    return admin


# ============================================================
# CURRENT ADMIN FROM SESSION
# ============================================================

def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> Admin:
    """
    Return the currently authenticated admin.

    If there is no valid authenticated session,
    stop the request and redirect the browser to /login.
    """

    admin_id = request.session.get("admin_id")

    if admin_id is None:
        raise HTTPException(
            status_code=303,
            headers={
                "Location": "/login",
            },
        )

    admin = db.scalar(
        select(Admin).where(
            Admin.id == admin_id,
            Admin.is_active.is_(True),
        )
    )

    if admin is None:
        request.session.clear()

        raise HTTPException(
            status_code=303,
            headers={
                "Location": "/login",
            },
        )

    return admin