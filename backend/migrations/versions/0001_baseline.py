"""Baseline schema.

The application created its tables with Base.metadata.create_all before Alembic
was introduced. This revision adopts that schema as the starting point.

create_all(checkfirst=True) makes this a no-op on a database that already has
the tables, so it is safe to run `alembic upgrade head` against an existing
deployment, or `alembic stamp 0001_baseline` if you would rather not re-run it.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-20
"""

from typing import Sequence, Union

from alembic import op

from app.core.database import Base
import app.models  # noqa: F401  (registers every model on Base.metadata)

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
