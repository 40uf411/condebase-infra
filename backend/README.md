# Backend

FastAPI BFF for Keycloak auth flows with Redis-backed sessions.

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

## Environment

See `.env.example` for required settings.
