# Function Reference

Reference map for key backend/frontend functions and classes.

## Backend

### Configuration (`backend/app/core/config.py`)

- `Settings`: typed environment contract.
- `get_settings`: cached settings loader.
- Validators normalize and enforce:
  - URLs
  - CORS origin list
  - cookie domain behavior
  - session signing key map
  - security limits
  - background queue parameters
  - notification provider settings
  - entity model path

### Security Helpers (`backend/app/core/security.py`)

- `generate_state`: OIDC state token.
- `generate_code_verifier`: PKCE verifier.
- `challenge_from_verifier`: PKCE `S256` challenge.
- `safe_return_to`: safe redirect path validator.
- `sign_session_cookie`: signed cookie formatter.
- `verify_session_cookie`: signed cookie verifier.
- `request_client_ip`: client IP extraction.

### Authorization (`backend/app/core/authorization.py`)

- `extract_roles`: derive roles from userinfo/access-token claims.
- `permissions_for_roles`: role -> permission resolution.
- `effective_permissions`: session permission resolver.
- `ensure_permissions`: raises `403` for missing permissions.

### Error Model (`backend/app/core/errors.py`)

- `default_error_code`: status-code to stable error-code mapper.
- `error_response`: canonical API error envelope builder.
- `http_exception_handler`: HTTPException normalization.
- `request_validation_exception_handler`: 422 issues normalization.
- `unhandled_exception_handler`: safe 500 fallback.

### Session and Redis (`backend/app/services/sessions.py`, `backend/app/stores/redis_store.py`)

- `create_session`: persist session payload.
- `get_session`: load + refresh TTL.
- `delete_session`: remove session.
- `RedisStore.set_json/get_json/delete/expire`.
- `RedisStore.set_value/get_value`.
- `RedisStore.increment_with_window`: rate-limit counter primitive.
- `RedisStore.ttl`: key TTL query.

### OIDC Integration (`backend/app/services/keycloak_oidc.py`)

- `build_authorize_url`: login/register authorization URL.
- `exchange_code_for_tokens`: code -> token exchange.
- `refresh_tokens`: refresh token exchange.
- `fetch_userinfo`: user claims fetch.
- `fetch_account_profile`: account profile fetch.
- `update_web_preferences`: update Keycloak preference attribute.
- `build_logout_url`: RP-initiated logout URL.

### Rate Limit and Bruteforce (`backend/app/services/rate_limit.py`)

- `consume_rate_limit`: generic limit consumption and retry metadata.
- `auth_bruteforce_block_ttl`: block-status query.
- `register_auth_failure`: failed-login tracking.
- `clear_auth_failures`: reset failure counters.

### Activity Logging (`backend/app/services/activity_logger.py`, `backend/app/stores/activity_store.py`)

- `ActivityLogger.log_event`: structured audit/security event logging.
- `ActivityStore.append`: persistence adapter for log events.
- `ActivityStore.initialize`: DB connectivity check (table lifecycle is migration-managed).

### App User Store (`backend/app/stores/user_store.py`)

- `AppUserStore.initialize`: DB connectivity check.
- `AppUserStore.upsert_user`: mirror profile/preferences into `app_users`.

### Dynamic Entities

#### Model Schema (`backend/app/entities/model.py`)

- `load_entity_model_from_dict`: model validation + normalization.
- `load_entity_model_from_file`: file loader.
- `entity_model_to_dict`: normalized serializer.

#### Store (`backend/app/stores/entity_store.py`)

- `EntityStore.initialize`: load model and ensure generated tables/indexes.
- `EntityStore.entity_metadata`: safe schema discovery payload.
- `EntityStore.create_record/get_record/list_records/update_record/soft_delete_record`.
- Security properties:
  - UUID normalization for record ids
  - parameterized SQL
  - soft-delete filtering
  - paginated list reads (`limit`, `offset`)

### Background Jobs (`backend/app/services/job_queue.py`, `backend/app/services/job_executor.py`, `backend/app/worker.py`)

- `JobQueue.enqueue`: push job (immediate or delayed).
- `JobQueue.dequeue`: pop next job for worker.
- `JobQueue.promote_due_jobs`: delayed -> active promotion.
- `JobQueue.schedule_retry`: retry scheduling.
- `JobQueue.move_to_dead_letter`: dead-letter routing.
- `JobQueue.metrics`: queue depth metrics.
- `JobExecutor.execute`: dispatch by job type.
- `run_worker`: long-running worker loop.

### Notifications (`backend/app/notifications/service.py`, `backend/app/notifications/providers/*`)

- `NotificationService.create`: provider selection.
- `NotificationService.send_template_email`: template rendering + send.
- `NotificationService.send_raw_email`: raw payload send.
- Provider contract: `NotificationProvider.send_email`.
- Providers:
  - `LogNotificationProvider`
  - `SmtpNotificationProvider`
  - `SesNotificationProvider`

### API Dependencies (`backend/app/api/deps.py`)

- `optional_session` / `require_session`.
- `require_permissions`: RBAC dependency factory.
- `require_csrf`: CSRF enforcement helper.
- `get_*` helpers for stores/services via `app.state`.
- cookie helpers: `set_auth_cookies`, `clear_auth_cookies`.

### Routers

#### `backend/app/api/routers/health.py`

- `healthz`

#### `backend/app/api/routers/auth.py`

- login/register start handlers
- callback handler
- `auth_me`
- `auth_logout`

#### `backend/app/api/routers/profile.py`

- `get_profile`
- `upload_profile_picture`
- `update_profile_preferences`

#### `backend/app/api/routers/jobs.py`

- enqueue handlers for email/webhook/image/task
- `job_metrics`

#### `backend/app/api/routers/entities.py`

- `list_entities`
- `create_entity_record`
- `list_entity_records`
- `get_entity_record`
- `update_entity_record`
- `delete_entity_record`

### App Composition (`backend/app/main.py`)

- `lifespan`: service/store initialization and teardown.
- `security_and_activity_middleware`: request id, rate limit, headers, activity log.
- global exception handler registration.
- API router and static media mounts.

## Frontend

### API (`frontend/src/api.js`)

- `buildApiUrl`
- `getCookieValue`
- `requestJson`
- `createRequestError`
- `resolveApiErrorMessage`
- `getApiValidationIssues`
- auth/profile operations:
  - `fetchAuthState`
  - `fetchProfile`
  - `updateUserPreferences`
  - `uploadProfilePicture`
  - `logout`
  - `buildLoginUrl`
  - `buildRegistrationUrl`
  - `startLogin`
  - `startRegistration`

### Hooks (`frontend/src/hooks/useApiError.js`)

- `useApiError`
  - `getErrorMessage`
  - `getValidationIssues`

### UI Root (`frontend/src/App.jsx`)

- `App`: global state orchestration and route shell.
- `ProfilePage`: authenticated user view + picture upload.
- `LandingPage`: signed-in/signed-out landing view.
- `DetailsPanel`, `TerminalPanel`, `StatusPill`, helper UI components.

### Theme and i18n

- theme modules: `theme-light.js`, `theme-dark.js`
- css token layers: `styles/theme-light.css`, `styles/theme-dark.css`
- translations: `src/i18n/dictionaries/*.js`
