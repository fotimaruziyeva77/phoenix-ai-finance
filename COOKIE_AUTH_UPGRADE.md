# Cookie-based auth upgrade notes

## Backend

1. Set **`APP_AUTH_COOKIE_ENABLED=true`**, **`APP_CORS_ALLOW_CREDENTIALS=true`**, and list exact SPA origins in **`APP_CORS_ORIGINS`** (no `*`).
2. Optional **`APP_AUTH_COOKIE_OMIT_BODY_TOKENS=true`** to stop returning JWTs in JSON (HttpOnly cookies only); the Next.js app must use **`NEXT_PUBLIC_AUTH_COOKIE_MODE=true`**.
3. New endpoint **`GET /api/v1/auth/bootstrap`**: returns `authenticated`, `user`, `csrf_token`, `auth_transport` for SPA hydration.
4. **`POST /api/v1/auth/refresh`** accepts an empty body when the refresh JWT is sent as the **`bf_refresh`** cookie; **`X-CSRF-Token`** must match **`bf_csrf`** when any auth cookie is present on mutating requests (except register, login, oauth exchange).
5. **`POST /api/v1/auth/logout`**, **`logout-all`**, **`logout-current`** clear session cookies when cookie mode is on.

## Frontend

1. Set **`NEXT_PUBLIC_AUTH_COOKIE_MODE=true`** to match the API.
2. The app hydrates via **`/api/v1/auth/bootstrap`** with **`credentials: 'include'`** and no longer relies on localStorage for primary auth in that mode.
3. Mutating `apiFetch` calls attach **`X-CSRF-Token`** from the login/bootstrap response (and in-memory store).

## OAuth

Google/GitHub flows are unchanged for providers; exchange still returns the same JSON envelope plus **`Set-Cookie`** when cookie mode is enabled. Misconfiguration now surfaces explicit missing-variable hints from **`GoogleOAuthNotConfiguredError`** / **`GithubOAuthNotConfiguredError`**.
