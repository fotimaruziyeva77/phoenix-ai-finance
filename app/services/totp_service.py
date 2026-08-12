"""TOTP 2FA lifecycle: setup, activate, verify, disable."""

from __future__ import annotations

import secrets
import uuid

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.lib.integration_secrets_crypto import decrypt_integration_secret, encrypt_integration_secret
from app.models.user_totp import UserTotp

_LOG = get_logger(__name__)
_HASHER = PasswordHasher()
_RECOVERY_CODE_COUNT = 8


class TotpError(Exception):
    code: str = "totp_error"
    status_code: int = 400

    def __init__(self, message: str = "TOTP operation failed") -> None:
        self.message = message
        super().__init__(message)


class TotpAlreadyActiveError(TotpError):
    code = "totp_already_active"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("2FA is already active for this account.")


class TotpNotConfiguredError(TotpError):
    code = "totp_not_configured"
    status_code = 404

    def __init__(self) -> None:
        super().__init__("2FA is not configured for this account.")


class TotpInvalidCodeError(TotpError):
    code = "totp_invalid_code"
    status_code = 422

    def __init__(self) -> None:
        super().__init__("Invalid TOTP code.")


def _generate_recovery_codes() -> list[dict]:
    """Generate hashed one-time recovery codes."""
    codes: list[dict] = []
    plain_codes: list[str] = []
    for _ in range(_RECOVERY_CODE_COUNT):
        code = secrets.token_hex(4).upper()  # 8-char hex
        plain_codes.append(code)
        codes.append({"hash": _HASHER.hash(code), "used": False})
    return codes, plain_codes  # type: ignore[return-value]


class TotpService:
    """Manage TOTP 2FA for users."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def get_totp_status(self, user_id: uuid.UUID) -> dict:
        """Return 2FA status for the user."""
        row = await self._get_totp_row(user_id)
        return {
            "is_configured": row is not None,
            "is_active": row.is_active if row else False,
        }

    async def setup_totp(self, user_id: uuid.UUID, email: str) -> dict:
        """Generate a new TOTP secret (or return pending one) and provisioning URI."""
        existing = await self._get_totp_row(user_id)
        if existing is not None and existing.is_active:
            raise TotpAlreadyActiveError()

        # Generate new secret
        secret = pyotp.random_base32()
        encrypted_secret = encrypt_integration_secret(secret, self._settings)

        # Generate recovery codes
        recovery_data, plain_codes = _generate_recovery_codes()

        if existing is not None:
            # Replace pending setup
            existing.secret_encrypted = encrypted_secret
            existing.is_active = False
            existing.recovery_codes_json = recovery_data
        else:
            row = UserTotp(
                user_id=user_id,
                secret_encrypted=encrypted_secret,
                is_active=False,
                recovery_codes_json=recovery_data,
            )
            self._session.add(row)

        await self._session.flush()
        await self._session.commit()

        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=email, issuer_name="BotForge")

        return {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "recovery_codes": plain_codes,
        }

    async def activate_totp(self, user_id: uuid.UUID, code: str) -> bool:
        """Verify first TOTP code and activate 2FA."""
        row = await self._get_totp_row(user_id)
        if row is None:
            raise TotpNotConfiguredError()
        if row.is_active:
            raise TotpAlreadyActiveError()

        secret = decrypt_integration_secret(row.secret_encrypted, self._settings)
        totp = pyotp.TOTP(secret)

        if not totp.verify(code, valid_window=1):
            raise TotpInvalidCodeError()

        row.is_active = True
        await self._session.flush()
        await self._session.commit()

        _LOG.info("totp_activated", user_id=str(user_id))
        return True

    async def verify_totp(self, user_id: uuid.UUID, code: str) -> bool:
        """Verify a TOTP code during login."""
        row = await self._get_totp_row(user_id)
        if row is None or not row.is_active:
            raise TotpNotConfiguredError()

        secret = decrypt_integration_secret(row.secret_encrypted, self._settings)
        totp = pyotp.TOTP(secret)

        # Try TOTP code first (valid_window=1 allows 30s clock skew)
        if totp.verify(code, valid_window=1):
            return True

        # Try recovery code
        if row.recovery_codes_json:
            for entry in row.recovery_codes_json:
                if entry.get("used"):
                    continue
                try:
                    _HASHER.verify(entry["hash"], code.upper())
                    entry["used"] = True
                    # Mark JSON as modified for SQLAlchemy
                    from sqlalchemy.orm.attributes import flag_modified  # noqa: PLC0415
                    flag_modified(row, "recovery_codes_json")
                    await self._session.flush()
                    await self._session.commit()
                    _LOG.info("totp_recovery_code_used", user_id=str(user_id))
                    return True
                except VerifyMismatchError:
                    continue

        raise TotpInvalidCodeError()

    async def disable_totp(self, user_id: uuid.UUID) -> None:
        """Remove 2FA for the user."""
        row = await self._get_totp_row(user_id)
        if row is None:
            raise TotpNotConfiguredError()
        await self._session.delete(row)
        await self._session.flush()
        await self._session.commit()
        _LOG.info("totp_disabled", user_id=str(user_id))

    async def is_totp_active(self, user_id: uuid.UUID) -> bool:
        """Quick check used during login flow."""
        row = await self._get_totp_row(user_id)
        return row is not None and row.is_active

    async def _get_totp_row(self, user_id: uuid.UUID) -> UserTotp | None:
        stmt = select(UserTotp).where(UserTotp.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
