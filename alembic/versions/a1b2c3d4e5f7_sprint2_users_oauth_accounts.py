"""sprint2 users and oauth_accounts

Revision ID: a1b2c3d4e5f7
Revises: 5357abad2fe8
Create Date: 2026-03-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "5357abad2fe8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: types may already exist from a failed/partial run. SQLAlchemy's
    # ENUM.create(checkfirst=True) + op.create_table can still emit duplicate CREATE TYPE;
    # raw DO blocks avoid that. Column types use create_type=False so CREATE TABLE never
    # emits CREATE TYPE.
    # asyncpg: one statement per execute (no multiple commands in one prepared stmt).
    op.execute(
        sa.text(
            """
            DO $$ BEGIN
                CREATE TYPE user_role AS ENUM ('customer_admin', 'superadmin');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$ BEGIN
                CREATE TYPE oauth_provider AS ENUM ('google', 'github');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )

    user_role = postgresql.ENUM(
        "customer_admin",
        "superadmin",
        name="user_role",
        create_type=False,
    )
    oauth_provider = postgresql.ENUM(
        "google",
        "github",
        name="oauth_provider",
        create_type=False,
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=256), nullable=True),
        sa.Column(
            "role",
            user_role,
            server_default=sa.text("'customer_admin'::user_role"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "oauth_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", oauth_provider, nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=320), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_oauth_provider_user",
        ),
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_oauth_accounts_user_id", table_name="oauth_accounts")
    op.drop_table("oauth_accounts")
    op.drop_table("users")

    bind = op.get_bind()
    postgresql.ENUM(name="oauth_provider", create_type=False).drop(bind, checkfirst=True)
    postgresql.ENUM(name="user_role", create_type=False).drop(bind, checkfirst=True)
