# Rollback Runbook

Procedure to return to last known-good release.

## Rollback Triggers

- sustained API `5xx` after release
- broken auth/session behavior
- severe regression in core user flows
- data integrity risk from deployed code path

## Inputs

- target rollback commit/tag
- migration revision currently applied
- operator assigned to execute rollback

## Steps

1. Freeze further deploy activity.
2. Capture current diagnostics:
   ```bash
   cd infra
   docker compose ps
   docker compose logs --tail 300 backend worker frontend keycloak
   docker compose exec backend alembic current
   ```
3. Checkout previous stable commit/tag.
4. Rebuild/restart stack:
   ```bash
   cd infra
   docker compose up -d --build
   ```
5. Re-verify health and smoke tests.
6. If required, apply schema downgrade:
   ```bash
   docker compose exec backend alembic downgrade -1
   ```
   Use explicit revision if needed.

## Validation After Rollback

- `/healthz` healthy from `app.local` and `api.local`.
- login, logout, and profile flows work.
- error rate returns to baseline.

## Notes

- Prefer application rollback first.
- Use DB downgrade only for incompatible schema regressions.
- Preserve logs and timestamps for postmortem.
