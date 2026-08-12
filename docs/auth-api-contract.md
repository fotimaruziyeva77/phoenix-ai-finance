# Auth API contract

Single source of truth for **machine-readable** auth responses:

| Area | Location |
|------|-----------|
| Success models | `app/schemas/auth.py`, `app/schemas/user.py` (`AuthSessionResponse`, `TokenResponse`, `MeResponse`, …) |
| Error codes (auth) | `app/services/auth_exceptions.py` → `StandardErrorResponse` via `app/core/exception_handlers.py` |
| Documented code sets | `app/schemas/auth_contract.py` (`ALL_DOCUMENTED_AUTH_ERROR_CODES`, …) |
| OpenAPI response maps | `app/api/auth_openapi.py` (wired on `app/api/v1/auth.py`, OAuth routers, `oauth_exchange.py`) |
| Drift tests | `tests/test_auth_api_contract.py` |

## Success shapes

- **Register / login / OAuth exchange** → `AuthSessionResponse` (201 register, 200 login/exchange). In cookie mode, `access_token` / `refresh_token` may be `null` with tokens in HttpOnly cookies.
- **Refresh** → `TokenResponse` (200).
- **GET /auth/me** → `MeResponse` (user + optional `email_verified_at`, `plan_key`).
- **GET /auth/session** → `{ "authenticated": boolean }` (`SessionStatusResponse`).
- **GET /auth/bootstrap** → `AuthBootstrapResponse`.
- **GET /auth/sessions** → `{ "items": [ RefreshSessionRead, … ] }`.
- **POST logout / logout-current / logout-all** → `204` empty body; may send `Set-Cookie` clears in cookie mode.

## OAuth browser flow (not JSON)

Google/GitHub **callbacks** return **302** to `FRONTEND_OAUTH_REDIRECT_URL` with query:

- Success: `oauth_exchange_code=<one_time>` → client calls `POST /auth/oauth/exchange`.
- Failure: `oauth_error=<stable_code>`; optional `detail` if the API exposes error details.

Constants: `OAUTH_CALLBACK_QUERY_*` in `app/schemas/auth_contract.py`.

## Errors

All mapped auth domain errors use JSON:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "request_id": "string | null",
    "category": "authentication | null",
    "details": null
  }
}
```

Omitted keys use `exclude_none` on the server. Validation failures (422) use `code: "validation_error"` and `details` as a Pydantic error list. Missing refresh token (body + cookie) uses `code: "refresh_token_required"` (422, category `authentication`).

## Frontend

Types live in `frontend/src/types/auth.ts`; API wrappers in `frontend/src/lib/api/auth.ts`. Contract smoke tests: `frontend/src/types/auth.contract.test.ts`.

Regenerate or inspect OpenAPI at `/openapi.json` when `expose_docs` is enabled.
