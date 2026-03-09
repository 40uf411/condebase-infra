# Deploy Runbook

Release procedure for backend, worker, and frontend stack.

## Preconditions

- Release commit/tag is approved.
- `infra/.env` is validated for target environment.
- Database backup snapshot exists.
- Rollback plan and owner are assigned.

## Pre-Deploy Checks

1. Confirm repository state:
   ```bash
   git rev-parse --short HEAD
   ```
2. Confirm compose config resolves:
   ```bash
   cd infra
   docker compose config > /dev/null
   ```
3. Confirm image build dependencies are available.

## Deployment Steps

1. Pull release commit.
2. Start/update services:
   ```bash
   cd infra
   docker compose up -d --build
   ```
3. Confirm container status:
   ```bash
   docker compose ps
   ```
4. Verify migration state:
   ```bash
   docker compose exec backend alembic current
   docker compose exec backend alembic heads
   ```
5. Verify API health:
   - `https://app.local/api/healthz`
   - `https://api.local/healthz`
6. Verify critical paths:
   - login
   - logout
   - profile read
   - profile preference update
   - at least one `/jobs/*` enqueue endpoint
7. Inspect logs:
   ```bash
   docker compose logs --tail 200 backend worker frontend keycloak
   ```

## Exit Criteria

- All services healthy.
- `alembic current` equals `alembic heads`.
- No sustained `5xx` errors.
- Critical flows verified.

## Post-Deploy Notes

- Record deployed commit SHA and timestamp.
- Record any non-default steps taken during deployment.
