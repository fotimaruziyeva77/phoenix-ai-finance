"""deferred checks: password_hash NULL only when OAuth-linked

Revision ID: b3e4f5a6c7d9
Revises: a1b2c3d4e5f7
Create Date: 2026-03-29

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b3e4f5a6c7d9"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION users_enforce_password_or_oauth()
        RETURNS TRIGGER AS $$
        BEGIN
          IF NEW.password_hash IS NULL THEN
            IF NOT EXISTS (
              SELECT 1 FROM oauth_accounts WHERE user_id = NEW.id
            ) THEN
              RAISE EXCEPTION 'users.password_hash cannot be NULL without at least one oauth_account'
                USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_users_deferred_password_or_oauth
        AFTER INSERT OR UPDATE OF password_hash ON users
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE PROCEDURE users_enforce_password_or_oauth();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION oauth_accounts_enforce_user_auth_after_delete()
        RETURNS TRIGGER AS $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = OLD.user_id
              AND u.password_hash IS NULL
              AND NOT EXISTS (
                SELECT 1 FROM oauth_accounts o WHERE o.user_id = u.id
              )
          ) THEN
            RAISE EXCEPTION 'cannot remove last oauth_account while users.password_hash is NULL'
              USING ERRCODE = '23514';
          END IF;
          RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_oauth_accounts_deferred_after_delete
        AFTER DELETE ON oauth_accounts
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE PROCEDURE oauth_accounts_enforce_user_auth_after_delete();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_oauth_accounts_deferred_after_delete ON oauth_accounts"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_users_deferred_password_or_oauth ON users")
    op.execute("DROP FUNCTION IF EXISTS oauth_accounts_enforce_user_auth_after_delete()")
    op.execute("DROP FUNCTION IF EXISTS users_enforce_password_or_oauth()")
