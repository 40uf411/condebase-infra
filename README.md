# Keycloak Docker Auth App

Production-style local auth platform using:

- Keycloak (`auth.local`)
- FastAPI backend BFF (`api.local`, proxied under `app.local/api`)
- React SPA (`app.local`)
- Redis for sessions, rate-limit counters, and background queue
- PostgreSQL for app data (`app_users`, `activity_logs`, generated entity tables)

## Documentation Index

- `docs/CODE_STRUCTURE.md`: architecture, runtime flow, and module layout.
- `docs/FUNCTION_REFERENCE.md`: backend/frontend function-level reference.
- `docs/KEYCLOAK_USER_FIELDS_AND_ROLES.md`: Keycloak attribute/group/role modeling.
- `docs/RUNBOOK_DEPLOY.md`: release deployment checklist.
- `docs/RUNBOOK_ROLLBACK.md`: rollback procedure.
- `docs/RUNBOOK_RESTORE.md`: restore procedure.
- `docs/RUNBOOK_INCIDENT_CHECKLIST.md`: incident response checklist.
- `frontend/keycloak-theme/README.md`: theme build and Keycloak packaging.
- `backend/README.md`: backend-specific implementation and operations guide.

## Architecture At A Glance

- `https://app.local`: React SPA.
- `https://app.local/api/*`: FastAPI backend through Caddy same-origin proxy.
- `https://api.local`: direct backend endpoint for diagnostics.
- `https://auth.local`: Keycloak admin and OIDC endpoints.
- Redis stores login state, sessions, rate-limit counters, and job queues.
- Worker service consumes async jobs (email, webhooks, image processing, generic tasks).

Same-origin proxying through `app.local/api` is intentional. It avoids cross-site cookie issues and keeps browser auth behavior stable.

## Core Capabilities

### Authentication and Session

- OAuth 2.0 Authorization Code + PKCE with Keycloak.
- Registration entry path (`kc_action=register`).
- Session-based BFF architecture (tokens stored server-side, not in browser storage).
- RP-initiated logout through backend + Keycloak.

### Security Backbone

- Signed session cookie with key-id based secret rotation.
- Global and auth-specific rate limits (Redis counters).
- Login brute-force protection with temporary client-IP blocks.
- CSRF double-submit protection (`csrf_token` cookie + `X-CSRF-Token` header + session token).
- Security headers middleware.
- RBAC permissions (route/service level).
- Persistent activity logs (`activity_logs`).
- Standard API error envelope for all failures.

### Maintainability and Platform Growth

- Alembic migrations for core schema versioning (`app_users`, `activity_logs`).
- JSON-driven business model generator and dynamic CRUD (`/entities/*`).
- Notification module with provider abstraction (`log`, `smtp`, `ses`) and templates.
- Background job queue + worker with retry/dead-letter behavior.

## Prerequisites

- Docker Desktop
- Caddy at `C:\Tools\Caddy\caddy.exe`
- PostgreSQL database for Keycloak
- PostgreSQL database for backend app data

## Hosts File

Add:

```txt
127.0.0.1 auth.local
127.0.0.1 api.local
127.0.0.1 app.local
```

## Configuration

1. Copy `infra/.env.example` to `infra/.env`.
2. Set at minimum:
   - `KEYCLOAK_CLIENT_SECRET`
   - `DATABASE_URL`
   - `SESSION_SIGNING_KEYS`
   - `SESSION_SIGNING_ACTIVE_KEY_ID`

## Keycloak Client Setup

Realm: `auth_app`  
Client: `auth-app-bff` (confidential)

- Valid redirect URIs:
  - `https://app.local/api/auth/callback`
  - optional compatibility: `https://api.local/auth/callback`
- Valid post-logout redirect URIs:
  - `https://app.local/*`
- Web origins:
  - `https://app.local`
- Standard flow:
  - enabled
- Optional self-service registration:
  - Realm Settings -> Login -> `User registration` = ON

## Start The Stack

```powershell
cd infra
docker compose up --build
```

`backend` runs `alembic upgrade head` before starting the API server.

Start Caddy:

```powershell
C:\Tools\Caddy\caddy.exe run --config A:\workspace\keycloak-docker\infra\Caddyfile --adapter caddyfile
```

## Verify Endpoints

- `https://app.local`
- `https://app.local/api/healthz`
- `https://api.local/healthz`
- `https://auth.local`

## Runtime Flow Summary

1. SPA loads and calls `GET /api/auth/me`.
2. Login/Register redirects to `/api/auth/login` or `/api/auth/register`.
3. Backend stores one-time `state` + PKCE verifier in Redis.
4. Keycloak callback reaches `/api/auth/callback` with `code` and `state`.
5. Backend exchanges code, fetches userinfo, creates Redis session, sets cookies.
6. SPA reads auth state and profile.
7. Preference updates call `PUT /api/profile/preferences`.
8. Logout calls `POST /api/auth/logout`.

## Business Entity Expansion

1. Define entities in JSON (see `backend/examples/entities_model.example.json`).
2. Generate normalized model:

```bash
cd backend
python scripts/generate_entities.py --input examples/entities_model.example.json --output app/generated/entities_model.json
```

3. Start backend and use `/entities/*` endpoints.

All generated entities include base columns:

- `id` (`UUID`, primary key)
- `created_at`
- `updated_at`
- `deleted_at` (soft delete)

## Standard Error Envelope

All API errors use:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {},
    "status": 422,
    "requestId": "..."
  }
}
```

## Notes

- The Keycloak web preference attribute key is currently `web-prefrences` (intentional compatibility).
- Callback `state` values are one-time; replaying callback URLs returns an invalid/expired state error.
