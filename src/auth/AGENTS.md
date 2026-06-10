# Purpose

Upstox API v2/v3 OAuth 2.0 authentication lifecycle, daily access-token persistence, and rate-limit token bucket. The only module allowed to read or write credentials.

# Ownership

| File | Owner |
|------|-------|
| `__init__.py` | Upstox API Architect |
| `upstox_auth.py` | Upstox API Architect |
| `token_manager.py` | Upstox API Architect |

# Local Contracts

- **OAuth2 flow only:** Authorization Code Grant. No client-credentials, no password grant. `ALL_DOCS/UPSTOX-api-docs.json` is the canonical reference.
- **Token storage:** Token JSON must be written to `config/.access_token.json` with permissions `chmod 0600` (POSIX). Gitignored.
- **No in-memory token leaking:** Never `print()` or `logger.info` the access_token. Mask in any error output.
- **Token expiry handling:** Access token is valid until 3:30 AM the next day. The module must auto-detect expiry and trigger a fresh login flow on the next process start.
- **Rate limiting:** Outbound REST calls must be queued through a token bucket (capacity 200, refill 200 per 60 s — Upstox standard limit). Do not exceed.
- **No API call without `Authorization: Bearer <token>` header:** Assert this at the lowest HTTP helper layer.

# Work Guidance

- **Run once per day:** Login is manual (or selenium-driven in a future enhancement). Token file is then reused for the rest of the day.
- **Logout:** Implement `logout()` that calls Upstox revoke endpoint, deletes the token JSON, and returns 204.
- **CI/CD:** Never run real auth in CI. Inject a fake token via `monkeypatch` in tests.

# Verification

- `test_upstox_auth.py` must cover:
  - Token persists only if date matches.
  - Missing/expired token raises `TokenExpiredError`.
  - `chmod 0600` is enforced on POSIX.
- Manual check: `grep -r "access_token" src/auth/` must never log the raw token.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files required. Sub-modules are documented in the Ownership table above.
