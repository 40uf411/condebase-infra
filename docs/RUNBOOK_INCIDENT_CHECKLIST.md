# Incident Checklist

Operational checklist for active production/staging incidents.

## First 10 Minutes

1. Assign incident commander.
2. Record start time and impacted services.
3. Identify scope:
   - auth only
   - API-wide
   - worker queue only
   - infra-wide
4. Capture current state:
   ```bash
   cd infra
   docker compose ps
   docker compose logs --tail 300 backend worker frontend keycloak redis
   ```
5. Validate health:
   - `https://app.local/api/healthz`
   - `https://api.local/healthz`

## Triage

1. Check migrations:
   ```bash
   docker compose exec backend alembic current
   docker compose exec backend alembic heads
   ```
2. Check Redis availability (sessions + queue).
3. Check DB connectivity from backend.
4. Check Keycloak reachability from backend.
5. Check request-id correlated errors in backend logs.

## Containment

1. Execute rollback if release regression is confirmed.
2. Stop write paths if data integrity is at risk.
3. Tighten rate limits if abuse/brute-force is active.
4. Communicate current status and ETA.

## Recovery

1. Restore healthy deployment/database state.
2. Run smoke validation:
   - login
   - logout
   - profile read/update
   - one job enqueue + worker completion
3. Confirm error rate and latency return to baseline.

## Aftercare

1. Preserve logs and key metrics.
2. Publish incident timeline.
3. Open postmortem with:
   - root cause
   - impact window
   - contributing factors
   - detection gaps
   - action items and owners
