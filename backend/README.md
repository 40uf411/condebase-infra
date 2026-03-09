# Backend

FastAPI BFF service for Keycloak-based authentication, session management, security controls, business entity CRUD, and async processing.

## Directory Layout

```text
backend/
  alembic/                  # migration env + revisions
  app/
    api/                    # routers + dependencies
    core/                   # settings, security, authorization, errors
    domain/                 # business normalization rules
    entities/               # entity model schema parser/validator
    generated/              # normalized entity model JSON
    notifications/          # provider abstraction + templates
    services/               # OIDC, sessions, jobs, media, logging
    stores/                 # Redis/PostgreSQL persistence adapters
    main.py                 # application bootstrap
    worker.py               # background worker entrypoint
  scripts/                  # generators and utility scripts
  examples/                 # sample entity model input
  alembic.ini
  requirements.txt
```

## Security Backbone

- Signed session cookie with key-id based secret rotation.
- Global and auth flow rate limits with Redis counters.
- Login brute-force protection by client IP.
- Security headers middleware.
- CSRF enforcement for state-changing endpoints.
- RBAC permission checks via reusable dependencies.
- Persistent activity logging (`activity_logs`).

## API Conventions

### Error Envelope

All failures return:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "issues": [
        {
          "field": "body.language",
          "message": "Language must not be empty",
          "type": "value_error"
        }
      ]
    },
    "status": 422,
    "requestId": "..."
  }
}
```

### Pagination

Entity bulk reads use `limit` and `offset`.

### Soft Delete

Generated entity deletes set `deleted_at` and keep rows in place.

## Endpoints

### Health

- `GET /healthz`

### Auth

- `GET /auth/login?returnTo=/profile`
- `GET /auth/register?returnTo=/profile`
- `GET /auth/callback`
- `GET /auth/me`
- `POST /auth/logout` (CSRF)

### Profile

- `GET /profile`
- `POST /profile/picture` (multipart + CSRF)
- `PUT /profile/preferences` (JSON + CSRF)

### Jobs (admin permission)

- `POST /jobs/email/template`
- `POST /jobs/email/raw`
- `POST /jobs/webhook`
- `POST /jobs/image-process`
- `POST /jobs/task`
- `GET /jobs/metrics`

### Generated Entities

- `GET /entities` (metadata)
- `POST /entities/{entity}/records` (CSRF)
- `GET /entities/{entity}/records` (paged, optional `q`)
- `GET /entities/{entity}/records/{id}` (`id` must be UUID)
- `PATCH /entities/{entity}/records/{id}` (CSRF)
- `DELETE /entities/{entity}/records/{id}` (soft delete + CSRF)

## Database Schema Ownership

- Core tables (`app_users`, `activity_logs`) are migration-managed through Alembic.
- Generated business entity tables are model-driven through `EntityStore` at startup.

Run migrations from `backend/`:

```bash
alembic upgrade head
```

Create a revision:

```bash
alembic revision -m "describe change"
```

## Entity Model Generator

Generate normalized entity model JSON:

```bash
cd backend
python scripts/generate_entities.py --input examples/entities_model.example.json --output app/generated/entities_model.json
```

Rules:

- Primary key must be base `id`.
- Reserved base fields cannot be redefined.
- Foreign keys must use `table.column` format.
- Searchable fields are validated against defined attributes.

## Background Jobs and Notifications

- Worker queue backend: Redis.
- Job types: template email, raw email, webhook, image-processing, generic async task.
- Notification providers:
  - `log`
  - `smtp`
  - `ses`

## Local Development Notes

- See `.env.example` for required settings.
- Backend container startup applies migrations before boot.
- When changing entity model JSON, regenerate file and restart backend.
