# Code Structure

This document describes the current implementation, runtime flow, and security model.

## Top-Level Layout

```text
keycloak-docker/
  infra/                    # Docker Compose + Caddy reverse proxy
  backend/                  # FastAPI BFF/auth service
  frontend/                 # React + Vite SPA + Keycloak theme project
    keycloak-theme/         # Keycloakify login/register theme source
  docs/                     # Architecture and reference docs
  caddy_run.txt             # Local Caddy run command
  README.md                 # Setup/runbook + flow overview
```

## Infrastructure

Primary files:

- `infra/docker-compose.yml`
- `infra/Caddyfile`
- `infra/.env`
- `infra/.env.example`

Responsibilities:

- Starts `redis`, `keycloak`, `auth-backend`, and `auth-frontend`.
- Builds Keycloak from `frontend/keycloak-theme/Dockerfile.keycloak`, bundling the custom theme JAR.
- Uses external PostgreSQL for both Keycloak and the backend mirror table (`app_users`).
- Terminates local TLS with Caddy (`tls internal`).
- Routes:
  - `https://auth.local` -> Keycloak (`localhost:8080`)
  - `https://api.local` -> backend (`localhost:8000`) for direct diagnostics
  - `https://app.local` -> frontend (`localhost:3000`)
  - `https://app.local/api/*` -> backend (`localhost:8000`) through same-origin proxy

Why same-origin `/api` matters:

- Browser session cookies are more reliable when SPA and API share the same site.
- Reduces cross-site credential/cookie policy friction during local auth flows.

## Backend

### Layout

```text
backend/
  app/
    api/
      deps.py               # Cookie/session/CSRF dependencies
      router.py             # Aggregates all routers
      routers/
        auth.py             # /auth/login/register/callback/me/logout
        health.py           # /healthz
        profile.py          # /profile + picture + preferences
    core/
      config.py             # Typed settings + validators
      security.py           # PKCE + state + safe return-path helpers
    domain/
      preferences.py        # Preference normalize/serialize helpers
    services/
      keycloak_oidc.py      # OIDC authorize/token/userinfo/logout + profile updates
      media.py              # Avatar storage + validation helpers
      serializers.py        # Session -> API profile payload mapping
      sessions.py           # Session create/read/delete + TTL refresh
    stores/
      redis_store.py        # Redis JSON helpers
      user_store.py         # app_users table init + upsert
    main.py                 # FastAPI app + lifespan initialization
  requirements.txt
  .env.example
  Dockerfile
```

### Runtime Flow

1. `GET /auth/login` or `GET /auth/register`
- Backend generates OIDC `state` + PKCE verifier/challenge.
- Stores one-time login state in Redis (`login_state:<state>`).
- Redirects to Keycloak authorize endpoint.
- Registration adds `kc_action=register`.
- Login may pass `prompt=login` to force the Keycloak login screen.

2. `GET /auth/callback`
- Validates and consumes one-time `state`.
- Exchanges `code` for tokens at Keycloak token endpoint.
- Calls Keycloak `userinfo` endpoint for claims.
- Creates Redis session (`session:<session_id>`) with claims, tokens, CSRF token, and preferences.
- Sets `app_session` and `csrf_token` cookies.
- Redirects to SPA return path (default `/profile`).

3. `GET /auth/me`
- Resolves session from `app_session` cookie.
- Returns:
  - `authenticated` boolean
  - `user` payload
  - `csrfToken` for CSRF-protected requests

4. `GET /profile`
- Requires authenticated session.
- Returns expanded profile payload (including tokens for debug UI).

5. `POST /profile/picture`
- Requires authenticated session + CSRF token.
- Accepts multipart image upload (`file`).
- Saves avatar in `MEDIA_DIR/avatars`.
- Updates session `picture` field and returns updated profile.

6. `PUT /profile/preferences`
- Requires authenticated session + CSRF token.
- Validates `language` and `theme`.
- Updates Keycloak account attribute (`web-prefrences`).
- Handles access-token refresh once if Keycloak returns `401`.
- Mirrors preferences into `app_users` and updates session payload.

7. `POST /auth/logout`
- Requires authenticated session + CSRF token.
- Deletes Redis session and clears auth cookies.
- Returns Keycloak logout URL for frontend redirect.

### Session Model

- Session storage: Redis JSON payload keyed by session id.
- Sliding TTL: each successful read refreshes expiry.
- Browser stores only session/CSRF cookies; tokens remain server-side.
- Local profile-picture URL is persisted in session and rehydrated on login if a local avatar exists.

### Cookie Model

- `app_session`: HttpOnly, secure session id cookie.
- `csrf_token`: readable cookie used for `X-CSRF-Token`.
- `cookie_domain` normalization:
  - If configured domain is single-label (example `.local`), backend falls back to host-only cookies.

## Frontend

### Layout

```text
frontend/
  src/
    main.jsx               # React root + router wiring
    App.jsx                # Route shell + auth/profile UI
    api.js                 # Fetch wrappers and auth redirects
    theme-light.js         # MUI light theme
    theme-dark.js          # MUI dark theme
    i18n/                  # language dictionaries + helpers
    styles.css             # Visual system + animations (theme-variable based)
    styles/
      theme-light.css      # CSS variable tokens for light mode
      theme-dark.css       # CSS variable tokens for dark mode
  index.html
  package.json
  vite.config.js
  .env.example
  Dockerfile
```

### Runtime Behavior

1. Startup calls `GET /api/auth/me` (`fetchAuthState`) with credentials.
2. Signed-out state:
- Shows login and registration actions.
- Login uses `prompt=login` (forced credentials prompt).
3. Signed-in state:
- `/profile` fetches `GET /api/profile` and renders profile + token + claims panels.
4. Preference updates:
- UI calls `PUT /api/profile/preferences` (`updateUserPreferences`).
- Backend persists preferences to Keycloak + `app_users` + session payload.
5. Picture updates:
- UI calls `POST /api/profile/picture` (`uploadProfilePicture`) with multipart form-data.
6. Logout:
- `POST /api/auth/logout` with `X-CSRF-Token`.
- Browser redirects to backend-provided Keycloak logout URL.

## Keycloak Theme (Login/Register)

### Layout

```text
frontend/keycloak-theme/
  src/
    main.tsx                         # Detect Keycloak context vs local dev mode
    main-kc.tsx                      # Real Keycloak runtime entry
    main-kc.dev.tsx                  # Local preview/dev entry
    kc.gen.tsx                       # Generated by keycloakify update-kc-gen
    login/                           # Login/register page implementation
      styleLevelCustomization.tsx    # Class mapping + custom stylesheet loader
  public/
    theme-overrides.css              # Theme palette/layout overrides
  Dockerfile.keycloak                # Multi-stage build that injects theme JAR into Keycloak
  package.json
```

### Runtime Behavior

1. `keycloakify` builds a theme JAR into `dist_keycloak/`.
2. `infra/docker-compose.yml` builds the `keycloak` service using `Dockerfile.keycloak`.
3. The final Keycloak image copies the generated JAR to `/opt/keycloak/providers`.
4. Realm setting `Login Theme` must be `auth-console-theme`.

## Protocols And Security Controls

- OIDC/OAuth 2.0 Authorization Code flow with PKCE.
- HTTPS local TLS via Caddy for all public hosts.
- Cookie-based backend sessions (BFF pattern).
- CSRF double-submit protection.
- Strict return path validation (`safe_return_to`) to block open redirects.
- CORS allow-list with credentials and wildcard guardrails.
