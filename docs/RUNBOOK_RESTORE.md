# Restore Runbook

Procedure for recovering service/data from backup.

## Restore Scenarios

- database corruption
- accidental destructive changes
- host-level failure requiring environment rebuild

## Inputs

- verified backup artifact and timestamp
- target PostgreSQL instance
- target release commit/tag

## Steps

1. Announce maintenance mode.
2. Stop write-path services:
   ```bash
   cd infra
   docker compose stop backend worker
   ```
3. Restore PostgreSQL from backup using your database tooling.
4. Start backend:
   ```bash
   docker compose up -d backend
   ```
5. Apply migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
6. Start remaining services:
   ```bash
   docker compose up -d worker frontend keycloak redis
   ```
7. Validate:
   - `GET /healthz`
   - login flow
   - profile read/update
   - activity log writes
   - job enqueue + worker processing

## Exit Criteria

- application healthy and serving traffic
- migration head reached
- key user flows and job pipeline operational
- restored data timestamp confirmed

## Follow-Up

- Document restore timeline.
- Capture root cause and preventive actions.
