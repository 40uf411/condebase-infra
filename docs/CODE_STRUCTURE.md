# Code Structure

This document describes repository structure, runtime architecture, and operational boundaries.

## Top-Level Layout

```text
keycloak-docker/
  infra/                    # Docker Compose, Caddy, environment files
  backend/                  # FastAPI BFF + worker + migrations
  frontend/                 # React SPA
  docs/                     # architecture, function reference, runbooks
  README.md                 # platform-level setup and flow
```

## Infrastructure Layer

Primary files:

- `infra/docker-compose.yml`
- `infra/Caddyfile`
- `infra/.env`
- `infra/.env.example`

Services:

- `redis`: session/cache/queue backbone.
- `keycloak`: identity provider with custom theme image.
- `backend`: FastAPI API server.
- `worker`: async job consumer.
- `frontend`: Vite/React app.

Traffic:

- `https://app.local` -> frontend.
- `https://app.local/api/*` -> backend (same-origin proxy).
- `https://api.local` -> backend direct diagnostics endpoint.
- `https://auth.local` -> Keycloak.

Migration behavior:

- Backend container runs `alembic upgrade head` before API startup.

## Backend Layer

```text
backend/
  alembic/
    env.py
    versions/
  app/
    api/
      deps.py
      router.py
      routers/
        auth.py
        health.py
        profile.py
        jobs.py
        entities.py
    core/
      config.py
      security.py
      authorization.py
      errors.py
    domain/
      preferences.py
    entities/
      model.py
    generated/
      entities_model.json
    notifications/
      providers/
      templates/
      service.py
    services/
      activity_logger.py
      job_queue.py
      job_executor.py
      keycloak_oidc.py
      rate_limit.py
      sessions.py
      serializers.py
      media.py
    stores/
      redis_store.py
      user_store.py
      activity_store.py
      entity_store.py
    main.py
    worker.py
  scripts/
    generate_entities.py
  examples/
    entities_model.example.json
  alembic.ini
  requirements.txt
  Dockerfile
```

## Backend Runtime Flow

### App startup (`app/main.py`)

1. Load settings.
2. Initialize stores/services:
   - Redis store
   - user store
   - activity store
   - entity store
   - notification service
   - job queue
3. Attach initialized objects to `app.state`.
4. Register middleware and global exception handlers.

### Request middleware

1. Generate `request_id`.
2. Resolve optional authenticated session.
3. Enforce global rate limits.
4. Apply security headers.
5. Log request event to activity log.

### Auth flow

1. `/auth/login` or `/auth/register` issues OIDC state + PKCE and redirects to Keycloak.
2. `/auth/callback` validates state, exchanges code, fetches claims, creates Redis session, sets cookies.
3. `/auth/me` returns auth status + profile summary + CSRF token.
4. `/auth/logout` enforces CSRF, clears session/cookies, returns Keycloak logout URL.

### Profile flow

- `/profile`: authenticated profile payload.
- `/profile/picture`: avatar upload + session update + background job enqueue.
- `/profile/preferences`: update Keycloak preference attribute + session + app DB mirror.

### Jobs flow

- `/jobs/*` endpoints enqueue work into Redis.
- Worker process pulls queue, executes handlers, retries failures, and dead-letters exhausted jobs.

### Dynamic entity flow

1. Generator validates and normalizes model JSON.
2. Backend loads generated model at startup.
3. `EntityStore` ensures tables/indexes exist for model entities.
4. `/entities/*` provides secured CRUD:
   - UUID id validation
   - soft delete filter
   - paginated list
   - parameterized search

## Data Ownership

### Migration-managed core schema

- `app_users`
- `activity_logs`
- tracked by Alembic revisions under `backend/alembic/versions`

### Model-driven generated schema

- business entity tables from `app/generated/entities_model.json`
- created/updated by `EntityStore` logic at startup

## Security Model

- OIDC Authorization Code + PKCE.
- Cookie session auth (`app_session`) with HMAC signature and key rotation.
- CSRF double-submit pattern.
- Global and auth rate limits.
- Login brute-force protection.
- Security headers middleware.
- RBAC permission checks (route and service-level usage).
- Activity logging with request context.
- Standard error envelope:
  - `error.code`
  - `error.message`
  - `error.details`
  - `error.status`
  - `error.requestId`

## Frontend Layer

```text
frontend/
  src/
    App.jsx
    api.js
    hooks/
      useApiError.js
    i18n/
    styles.css
    styles/
      theme-light.css
      theme-dark.css
    theme-light.js
    theme-dark.js
    main.jsx
  keycloak-theme/
    ...
```

Frontend behavior:

- `api.js` centralizes fetch calls and normalized API error parsing.
- `useApiError` hook provides reusable error messaging/issue extraction.
- `App.jsx` orchestrates auth state, navigation, profile actions, and preferences.

## Keycloak Theme Layer

- Source: `frontend/keycloak-theme/`
- Build output JAR injected into Keycloak image by `frontend/keycloak-theme/Dockerfile.keycloak`.
- Custom email theme files copied into Keycloak themes directory.

## Docs Layer

- `docs/FUNCTION_REFERENCE.md`: function-level map.
- `docs/KEYCLOAK_USER_FIELDS_AND_ROLES.md`: Keycloak modeling guide.
- `docs/RUNBOOK_*.md`: deploy, rollback, restore, and incident operations.
