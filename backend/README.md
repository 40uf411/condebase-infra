# Backend

FastAPI BFF for Keycloak auth flows with Redis-backed sessions.

## Security Backbone

- Signed session cookies with key-id based secret rotation support.
- Redis-backed global/API and auth-specific rate limiting.
- Login brute-force lockouts by client IP.
- Security headers middleware (`HSTS`, `X-Frame-Options`, `X-Content-Type-Options`, etc.).
- RBAC permission checks with reusable route dependencies.
- Persistent activity logging (`activity_logs`) for request and auth/profile security events.
- Redis-backed background job queue with dedicated worker process.
- Notification module with provider abstraction (`log`, `smtp`, `ses`) and file-based email templates.

### Session Secret Rotation

1. Add the new secret under a new key id in `SESSION_SIGNING_KEYS`.
2. Switch `SESSION_SIGNING_ACTIVE_KEY_ID` to the new key id.
3. Keep the previous key in `SESSION_SIGNING_KEYS` until old sessions expire.

## Structure

```
app/
  api/         # HTTP layer: routers and request dependencies
  core/        # Configuration and security utilities
  domain/      # Business rules and preference normalization
  services/    # Keycloak, media, session, and response composition logic
  stores/      # Redis and Postgres persistence adapters
  main.py      # Application bootstrap (lifespan, middleware, mounts)
```

## Endpoints

- `GET /healthz`
- `GET /auth/login?returnTo=/profile`
- `GET /auth/register?returnTo=/profile`
- `GET /auth/callback`
- `GET /auth/me`
- `POST /auth/logout`
- `GET /profile`
- `POST /profile/picture` (multipart upload, CSRF-protected)
- `PUT /profile/preferences` (JSON, CSRF-protected)
- `POST /jobs/email/template` (admin permission)
- `POST /jobs/email/raw` (admin permission)
- `POST /jobs/webhook` (admin permission)
- `POST /jobs/image-process` (admin permission)
- `POST /jobs/task` (admin permission)
- `GET /jobs/metrics` (admin permission)
- `GET /entities` (metadata list)
- `POST /entities/{entity}/records`
- `GET /entities/{entity}/records` (paged, optional `q` search)
- `GET /entities/{entity}/records/{id}` (`id` must be UUID)
- `PATCH /entities/{entity}/records/{id}`
- `DELETE /entities/{entity}/records/{id}` (soft delete)

## Environment

See `.env.example` for required settings.

## Entity Model Generator

1. Define entities in JSON (see `examples/entities_model.example.json`).
2. Generate normalized model:
   `python scripts/generate_entities.py --input examples/entities_model.example.json --output app/generated/entities_model.json`
3. Start backend; tables and CRUD endpoints are initialized automatically from the generated model.
