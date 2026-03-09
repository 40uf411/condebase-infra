# Function Reference

Current function map for backend and frontend.

## Backend

### Configuration (`backend/app/core/config.py`)

- `Settings`: typed environment contract.
- `_normalize_url`: trims trailing slash from base URLs.
- `_empty_cookie_domain_to_none`: converts empty/single-label cookie domains to host-only behavior.
- `_normalize_allowed_cors_origins`: parses CORS env input (JSON list or comma-separated string).
- `_validate_allowed_cors_origins`: removes trailing slash, blocks wildcard `*`, enforces non-empty list.
- `_normalize_media_dir`: validates non-empty media directory path.
- `_normalize_database_url`: validates non-empty database URL.
- `_validate_max_avatar_mb`: enforces avatar size range.
- `_normalize_entities_model_path`: validates model definition path for generated entities.
- `keycloak_public_realm_base` / `keycloak_internal_realm_base`: derived realm URL helpers.
- `get_settings`: cached singleton settings loader.

### Entity Model Schema (`backend/app/entities/model.py`)

- `load_entity_model_from_dict`: validates and normalizes raw JSON entity definitions.
- `load_entity_model_from_file`: reads + validates model JSON from disk.
- `entity_model_to_dict`: emits normalized model payload for generator output.

### Security and Redirect Helpers (`backend/app/core/security.py`)

- `generate_state`: random OIDC state.
- `generate_code_verifier`: PKCE code verifier.
- `challenge_from_verifier`: PKCE S256 challenge.
- `safe_return_to`: sanitizes return path to prevent open redirects.
- `sign_session_cookie`: signs session id values with key-id aware HMAC.
- `verify_session_cookie`: validates signed session cookies.
- `request_client_ip`: extracts client ip from `X-Forwarded-For` or request socket info.

### Authorization (`backend/app/core/authorization.py`)

- `extract_roles`: derives effective roles from userinfo and decoded access-token claims.
- `permissions_for_roles`: maps role set to effective permission set.
- `ensure_permissions`: reusable RBAC guard that raises `403` on missing permissions.

### Redis and Sessions

- `backend/app/stores/redis_store.py`
  - `login_state_key`: Redis key namespace for one-time login states.
  - `session_key`: Redis key namespace for authenticated sessions.
  - `RedisStore.set_json` / `get_json` / `delete` / `expire`: JSON Redis primitives.
  - `RedisStore.set_value` / `get_value`: scalar Redis operations.
  - `RedisStore.increment_with_window`: atomic counter + TTL window helper for rate-limits.
  - `RedisStore.ttl`: key TTL lookup.
- `backend/app/services/sessions.py`
  - `create_session`: persists session payload.
  - `get_session`: reads and refreshes TTL (sliding session).
  - `delete_session`: removes session payload.

### Generated Entity Store (`backend/app/stores/entity_store.py`)

- `EntityStore.initialize`: loads model JSON and creates/updates entity tables.
- `EntityStore.entity_metadata`: returns safe entity schema metadata for API discovery.
- `EntityStore.create_record`: create entity row with base UUID + timestamps.
- `EntityStore.get_record`: fetch single row by UUID with soft-delete filter.
- `EntityStore.list_records`: paged bulk fetch with parameterized search.
- `EntityStore.update_record`: partial update with `updated_at` tracking.
- `EntityStore.soft_delete_record`: sets `deleted_at` and keeps record.

### Rate Limits and Brute-Force Controls (`backend/app/services/rate_limit.py`)

- `consume_rate_limit`: evaluates rolling-window limits and returns retry metadata.
- `auth_bruteforce_block_ttl`: checks current login block duration for an identifier.
- `register_auth_failure`: increments failed auth attempts and applies temporary block when threshold is reached.
- `clear_auth_failures`: clears brute-force counters after successful authentication.

### Background Jobs (`backend/app/services/job_queue.py`, `backend/app/services/job_executor.py`, `backend/app/worker.py`)

- `JobQueue.enqueue`: pushes jobs to the queue (or delayed queue) with retry metadata.
- `JobQueue.dequeue`: worker blocking pop from job queue.
- `JobQueue.promote_due_jobs`: moves due delayed jobs back to the active queue.
- `JobQueue.schedule_retry`: requeues failed jobs with backoff delay.
- `JobQueue.move_to_dead_letter`: stores exhausted jobs in dead-letter queue.
- `JobQueue.metrics`: returns queue/dead-letter depth counters.
- `JobExecutor.execute`: dispatches a queued job by type.
- `JobExecutor._execute_send_template_email` / `_execute_send_raw_email`: notification jobs.
- `JobExecutor._execute_webhook_delivery`: outbound webhook delivery with timeout control.
- `JobExecutor._execute_image_processing`: image post-processing metadata generation.
- `JobExecutor._execute_async_task`: generic async task runner.
- `run_worker` (`backend/app/worker.py`): long-running worker loop with retry/dead-letter handling.

### OIDC Integration (`backend/app/services/keycloak_oidc.py`)

- `KeycloakOIDC.build_authorize_url`: constructs authorize URL (supports `register` and optional `prompt`).
- `KeycloakOIDC.exchange_code_for_tokens`: auth code -> token response.
- `KeycloakOIDC.refresh_tokens`: refresh token -> new token response.
- `KeycloakOIDC.fetch_userinfo`: reads claims from userinfo endpoint.
- `KeycloakOIDC.fetch_account_profile`: fetches current user account profile from Keycloak account endpoint.
- `KeycloakOIDC.update_web_preferences`: updates `web-prefrences` user attribute in Keycloak.
- `KeycloakOIDC.build_logout_url`: constructs RP-initiated logout URL.

### Notifications (`backend/app/notifications/service.py`, `backend/app/notifications/providers/*`)

- `NotificationService.create`: selects provider backend (`log`, `smtp`, `ses`) from settings.
- `NotificationService.send_template_email`: renders subject/body templates and dispatches email.
- `NotificationService.send_raw_email`: dispatches prebuilt email payloads.
- `LogNotificationProvider.send_email`: log-based provider for local/dev.
- `SmtpNotificationProvider.send_email`: SMTP provider with optional STARTTLS/SSL auth.
- `SesNotificationProvider.send_email`: AWS SES provider using boto3.

### Preferences and App User Store

- `backend/app/domain/preferences.py`
  - `default_web_preferences`: returns default language/theme.
  - `is_supported_language`: validates language against supported set.
  - `normalize_language` / `normalize_theme`: normalize preference values.
  - `normalize_web_preferences`: parse and normalize language/theme payloads from claims/session input.
  - `extract_web_preferences`: reads preference attribute (`web-prefrences`) from claims map.
  - `serialize_web_preferences`: outputs normalized preferences as compact JSON.
- `backend/app/stores/user_store.py`
  - `AppUserStore.initialize`: ensures `app_users` table exists.
  - `AppUserStore.upsert_user`: upserts user row with mirrored preference payload (`web_preferences`, `preferred_language`, `theme`).

### Activity Logging (`backend/app/stores/activity_store.py`, `backend/app/services/activity_logger.py`)

- `ActivityStore.initialize`: ensures `activity_logs` table and indexes exist.
- `ActivityStore.append`: persists structured activity events.
- `ActivityLogger.log_event`: logs request/security/auth/profile events with actor + request context.

### Dependencies, Sessions, Cookies, CSRF (`backend/app/api/deps.py`)

- `get_redis_store`: app-state Redis accessor.
- `get_user_store`: app-state app user DB store accessor.
- `get_activity_store`: app-state activity store accessor.
- `get_activity_logger`: app-state activity logger accessor.
- `get_job_queue`: app-state background job queue accessor.
- `get_notification_service`: app-state notification service accessor.
- `get_entity_store`: app-state generated entity store accessor.
- `set_auth_cookies`: sets `app_session` + `csrf_token`.
- `clear_auth_cookies`: clears auth cookies.
- `_csrf_from_request`: extracts cookie/header CSRF values.
- `require_csrf`: validates CSRF triplet (cookie/header/session).
- `optional_session`: resolves session from cookie (or `None`).
- `require_session`: enforces authenticated session.
- `require_permissions`: RBAC dependency factory for route-level permission checks.

### Serialization (`backend/app/services/serializers.py`)

- `user_profile_payload`: maps session + userinfo claims to API response shape; optionally includes tokens.

### Media (`backend/app/services/media.py`)

- `ensure_media_directories`: creates upload directories at startup.
- `avatar_directory`: resolves the avatar directory path.
- `find_profile_picture_url`: resolves existing local avatar URL for a subject.
- `save_profile_picture`: validates and stores uploaded avatar image.

### Routes

- `backend/app/api/routers/health.py`
  - `healthz`: health endpoint.
- `backend/app/api/routers/auth.py`
  - `_app_url`: builds safe app redirect URLs.
  - `_sync_app_user_record`: mirrors authenticated user into `app_users` at callback time.
  - `_start_login`: shared login/register entry, stores one-time state, redirects to Keycloak.
  - `auth_login`: starts login flow, optional `prompt` pass-through.
  - `auth_register`: starts registration flow.
  - `auth_callback`: validates state, exchanges code, creates session, sets cookies, redirects back to app.
  - `auth_me`: returns auth state, user profile summary, and CSRF token.
  - `auth_logout`: CSRF-protected logout; deletes local session and returns Keycloak logout URL.
- `backend/app/api/routers/profile.py`
  - `PreferencesUpdateRequest`: payload model for preference updates.
  - `_persist_session`: rewrites current session after mutable profile updates.
  - `get_profile`: authenticated profile payload with tokens.
  - `upload_profile_picture`: CSRF-protected avatar upload endpoint (`POST /profile/picture`).
  - `update_profile_preferences`: CSRF-protected preference update endpoint (`PUT /profile/preferences`) that updates Keycloak, Redis session, and `app_users`.
- `backend/app/api/routers/jobs.py`
  - `enqueue_template_email`: queue template-based email notification job.
  - `enqueue_raw_email`: queue raw email notification job.
  - `enqueue_webhook`: queue webhook delivery job.
  - `enqueue_image_processing`: queue image post-processing job.
  - `enqueue_task`: queue generic async task job.
  - `job_metrics`: return queue/dead-letter depth.
- `backend/app/api/routers/entities.py`
  - `list_entities`: generated-model metadata endpoint.
  - `create_entity_record`: secure create per entity.
  - `list_entity_records`: secure paginated list per entity (+`q` search).
  - `get_entity_record`: secure fetch by UUID per entity.
  - `update_entity_record`: secure partial update per entity.
  - `delete_entity_record`: secure soft delete per entity.

### Application Wiring

- `backend/app/api/router.py`
  - `api_router`: aggregates `health`, `auth`, and `profile` routers.
- `backend/app/main.py`
  - `lifespan`: initializes/closes Redis, HTTP client, app user store, activity logger store, notification service, and job queue service.
  - `app`: FastAPI app with CORS middleware and API router mounted.
  - `security_and_activity_middleware`: request id injection, global rate limiting, security headers, and activity logging.
  - `root`: basic service status endpoint.

## Frontend

### API Layer (`frontend/src/api.js`)

- `buildApiUrl`: joins API base (`/api` default) and path.
- `getCookieValue`: cookie helper used as CSRF fallback.
- `requestJson`: fetch wrapper with `credentials: include` + JSON/error normalization.
- `fetchAuthState`: calls `GET /api/auth/me`.
- `fetchProfile`: calls `GET /api/profile`.
- `updateUserPreferences`: calls `PUT /api/profile/preferences`.
- `uploadProfilePicture`: calls `POST /api/profile/picture` with multipart body.
- `buildLoginUrl`: builds `GET /api/auth/login` URL and optional `prompt=login`.
- `buildRegistrationUrl`: builds `GET /api/auth/register` URL.
- `startLogin`: browser redirect to login URL.
- `startRegistration`: browser redirect to registration URL.
- `logout`: sends `POST /api/auth/logout` with CSRF header.

### UI Components (`frontend/src/App.jsx`)

- `App`: root state machine for auth status, routing, login/register/logout actions, and preference persistence.
- `NavButton`: sidebar nav action component.
- `LoadingPanel`: global loading state panel.
- `DetailsPanel`: preferences + context details panel.
- `IntroPage`: pre-auth landing screen.
- `LandingPage`: signed-out/signed-in home CTA view.
- `ProfilePage`: protected profile UI, including token/claims viewers and picture upload.
- `ProfileField`: key/value item renderer.
- `CodePanel`: code block panel.
- `TerminalPanel`: session activity console panel.
- `StatusPill`: footer status token.

### Bootstrap and Styling

- `frontend/src/main.jsx`
  - React mount and router wiring.
- `frontend/src/theme-light.js` / `frontend/src/theme-dark.js`
  - split MUI theme definitions (light/dark).
- `frontend/src/styles.css`
  - layout styling, gradients, and animation primitives using theme variables.
- `frontend/src/styles/theme-light.css` / `frontend/src/styles/theme-dark.css`
  - split CSS variable files for light/dark rendering.
