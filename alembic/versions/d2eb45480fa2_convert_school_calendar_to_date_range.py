"""convert school calendar to date range

Revision ID: d2eb45480fa2
Revises: 02dd78c38cd7
Create Date: 2026-08-13 13:08:26.277303

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2eb45480fa2"
down_revision: Union[str, Sequence[str], None] = "02dd78c38cd7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convert school_calendar from a single date
    into a start_date / end_date range.

    Existing one-day entries are preserved by copying
    the old date into both start_date and end_date.
    """

    # --------------------------------------------------------
    # Create replacement table
    # --------------------------------------------------------

    op.create_table(
        "school_calendar_new",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "start_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "end_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "day_type",
            sa.Enum(
                "SCHOOL",
                "WEEKEND",
                "HOLIDAY",
                "VACATION",
                "CLOSED",
                name="calendardaytype",
            ),
            nullable=False,
        ),
        sa.Column(
            "is_off",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --------------------------------------------------------
    # Copy existing data
    #
    # Every old one-day entry becomes:
    #
    # date -> start_date
    # date -> end_date
    # --------------------------------------------------------

    op.execute(
        """
        INSERT INTO school_calendar_new (
            id,
            start_date,
            end_date,
            title,
            day_type,
            is_off,
            created_at
        )
        SELECT
            id,
            date,
            date,
            title,
            day_type,
            is_off,
            created_at
        FROM school_calendar
        """
    )

    # --------------------------------------------------------
    # Remove old table
    # --------------------------------------------------------

    op.drop_table("school_calendar")

    # --------------------------------------------------------
    # Rename replacement table
    # --------------------------------------------------------

    op.rename_table(
        "school_calendar_new",
        "school_calendar",
    )

    # --------------------------------------------------------
    # Restore indexes
    # --------------------------------------------------------

    op.create_index(
        "ix_school_calendar_start_date",
        "school_calendar",
        ["start_date"],
        unique=False,
    )

    op.create_index(
        "ix_school_calendar_end_date",
        "school_calendar",
        ["end_date"],
        unique=False,
    )


def downgrade() -> None:
    """
    Convert school_calendar back to the old single-date format.

    For a multi-day range, the start_date is retained as
    the old date because the old schema could only represent
    one date.
    """

    # --------------------------------------------------------
    # Create old-format table
    # --------------------------------------------------------

    op.create_table(
        "school_calendar_old",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "day_type",
            sa.Enum(
                "SCHOOL",
                "WEEKEND",
                "HOLIDAY",
                "VACATION",
                "CLOSED",
                name="calendardaytype_old",
            ),
            nullable=False,
        ),
        sa.Column(
            "is_off",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --------------------------------------------------------
    # Copy data back
    #
    # For ranges, keep start_date as the old date.
    # --------------------------------------------------------

    op.execute(
        """
        INSERT INTO school_calendar_old (
            id,
            date,
            title,
            day_type,
            is_off,
            created_at
        )
        SELECT
            id,
            start_date,
            title,
            day_type,
            is_off,
            created_at
        FROM school_calendar
        """
    )

    # --------------------------------------------------------
    # Remove new table
    # --------------------------------------------------------

    op.drop_table("school_calendar")

    # --------------------------------------------------------
    # Restore old table
    # --------------------------------------------------------

    op.rename_table(
        "school_calendar_old",
        "school_calendar",
    )

    # --------------------------------------------------------
    # Restore old date index
    # --------------------------------------------------------

    op.create_index(
        "ix_school_calendar_date",
        "school_calendar",
        ["date"],
        unique=False,
    )