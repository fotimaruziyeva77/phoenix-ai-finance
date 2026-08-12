"""JWT validation errors (distinct from transport/auth flow exceptions)."""


class TokenError(Exception):
    """Base class for token handling failures."""


class TokenInvalidError(TokenError):
    """Malformed, wrong signature, wrong algorithm, or missing required claims."""


class TokenExpiredError(TokenError):
    """Token ``exp`` is in the past."""


class TokenTypeError(TokenError):
    """``token_type`` claim does not match the expected kind."""
