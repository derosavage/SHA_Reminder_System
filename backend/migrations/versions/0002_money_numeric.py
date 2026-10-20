"""Store money as exact decimal instead of binary float.

KES amounts were declared Float (double precision on PostgreSQL), so sums of
contributions and penalties could drift by fractions of a shilling. They are now
numeric(12,2), which is exact for a currency with two decimals.

SQLite is skipped: it has no ALTER COLUMN TYPE, and every SQLite database in
this project is created fresh from the models (which already use Numeric).

Revision ID: 0002_money_numeric
Revises: 0001_baseline
Create Date: 2026-10-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_money_numeric"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY_COLUMNS = [
    ("transactions", "amount"),
    ("users", "contribution_amount"),
    ("penalty_calculations", "monthly_contribution"),
    ("penalty_calculations", "total_contributions_due"),
    ("penalty_calculations", "penalty_amount"),
    ("penalty_calculations", "total_amount_due"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column in MONEY_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.Numeric(12, 2),
            existing_type=sa.Float(),
            postgresql_using=f"{column}::numeric(12,2)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column in MONEY_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.Float(),
            existing_type=sa.Numeric(12, 2),
            postgresql_using=f"{column}::double precision",
        )
