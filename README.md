# Keycloak Docker Auth App

Local auth stack with Keycloak (`auth.local`), FastAPI backend, Redis sessions, and React SPA (`app.local`).

Backend traffic for the SPA is same-origin through `https://app.local/api/*` (proxied by Caddy to FastAPI), which keeps cookie auth stable in modern browsers.

## Documentation

- `docs/CODE_STRUCTURE.md`: repository architecture, runtime flow, and security controls.
- `docs/FUNCTION_REFERENCE.md`: backend/frontend function reference.
- `docs/KEYCLOAK_USER_FIELDS_AND_ROLES.md`: how to add custom user fields, classes/ranks, and roles in Keycloak.
- `frontend/keycloak-theme/README.md`: Keycloakify theme build and customization notes.

## Architecture At A Glance

- `https://app.local` -> React + Vite SPA.
- `https://app.local/api/*` -> FastAPI backend (via Caddy reverse proxy).
- `https://auth.local` -> Keycloak UI and OIDC endpoints.
- `https://api.local` -> direct backend host (kept for diagnostics/manual API checks).
- Redis stores login state and authenticated sessions.

## Core Functionality

- Login with Keycloak using OAuth 2.0 Authorization Code + PKCE.
- Registration flow via Keycloak (`kc_action=register`).
- Session-based auth at backend (not token-in-browser architecture).
- Profile page showing user claims and tokens from backend session payload.
- Global user prefrences  for language and theme (`light` / `dark`) with i18n dictionaries.
- Preference persistence to Keycloak user attribute `web-prefrences` and mirrored app DB table `app_users`.
- Logout through backend + Keycloak RP-initiated logout.
- Forced login prompt on login action (`prompt=login`) so Keycloak login screen appears even when IdP SSO exists.
- Custom Keycloakify login/register theme packaged into the Keycloak container.

## Protocols And Security Mechanisms

- OIDC/OAuth 2.0:
  - Authorization endpoint (`/protocol/openid-connect/auth`)
  - Token endpoint (`/protocol/openid-connect/token`)
  - UserInfo endpoint (`/protocol/openid-connect/userinfo`)
  - RP-initiated logout (`/protocol/openid-connect/logout`)
- PKCE:
  - `code_challenge_method=S256`, verifier stored temporarily in Redis.
- HTTPS/TLS:
  - Caddy serves local TLS certs (`tls internal`) for `app.local`, `api.local`, `auth.local`.
- Cookie session auth:
  - `app_session` (HttpOnly) and `csrf_token` cookies, backend-validated session in Redis.
  - Host-only cookie fallback for single-label domains (`.local` config is normalized to host-only).
- CSRF protection:
  - Double-submit pattern: `csrf_token` cookie + `X-CSRF-Token` header + session token match.
- CORS:
  - Explicit origin allow-list, credentials enabled, wildcard blocked by settings validation.

## 1. Prerequisites

- Docker Desktop
- Caddy installed at `C:\Tools\Caddy\caddy.exe`
- External PostgreSQL for Keycloak (`keycloak` DB)
- External PostgreSQL for app backend (`appdb` DB used for `app_users` table)

## 2. Hosts File

Add:

```txt
127.0.0.1 auth.local
127.0.0.1 api.local
127.0.0.1 app.local
```

## 3. Configure Environment

Edit `infra/.env` and set:

- `KEYCLOAK_CLIENT_SECRET`
- any DB overrides needed for your local setup

## 4. Configure Keycloak Client

Realm: `auth_app`  
Client: `auth-app-bff` (confidential)

- Valid redirect URIs:
  - `https://app.local/api/auth/callback`
  - optional compatibility: `https://api.local/auth/callback`
- Valid post logout redirect URIs: `https://app.local/*`
- Web origins: `https://app.local`
- Standard flow enabled

Optional for self-service registration:

- Realm settings -> Login -> `User registration` = ON

## 5. Start Services

```powershell
cd infra
docker compose up --build
```

`docker compose up --build` also builds the `keycloak` image from `frontend/keycloak-theme/Dockerfile.keycloak` and injects the generated theme JAR.

## 6. Start Caddy

```powershell
C:\Tools\Caddy\caddy.exe run --config A:\workspace\keycloak-docker\infra\Caddyfile --adapter caddyfile
```

## 7. Endpoints

- `https://app.local` SPA
- `https://app.local/api/healthz` backend health through same-origin proxy
- `https://api.local/healthz` direct backend health
- `https://auth.local` Keycloak

## 8. Runtime Auth Flow

1. SPA calls `GET /api/auth/me` on load.
2. Login/Register redirects browser to `/api/auth/login` or `/api/auth/register`.
3. Backend stores one-time OIDC state + PKCE verifier in Redis.
4. Keycloak redirects to `/api/auth/callback` with `code` + `state`.
5. Backend exchanges code, fetches userinfo, creates Redis session, sets cookies, redirects to `/profile`.
6. SPA reads authenticated state and fetches `/api/profile`.
7. Theme/language updates call `PUT /api/profile/prefrences `, then backend updates Keycloak attribute + `app_users` table.

## 9. Activate Custom Keycloak Theme

In Keycloak Admin Console:

1. Open `https://auth.local/admin`.
2. Select realm `auth_app`.
3. Go to `Realm settings` -> `Themes`.
4. Set `Login Theme` to `auth-console-theme`.
5. Click `Save`.

If the updated styling does not appear immediately, clear browser cache and restart the `keycloak` container once.

## Notes

- Tokens are stored server-side in Redis session payload and shown by the profile screen for inspection.
- Callback `state` is one-time and consumed; revisiting callback URLs manually will return `Invalid or expired state`.
