"""Email normalization for auth (single definition; avoid importing private helpers)."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_domain(email: str) -> str | None:
    """Domain part only (for audit logs; avoids logging full addresses on failures)."""
    parts = normalize_email(email).split("@", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    return parts[1]
