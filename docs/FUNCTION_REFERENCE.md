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
- `keycloak_public_realm_base` / `keycloak_internal_realm_base`: derived realm URL helpers.
- `get_settings`: cached singleton settings loader.

### Security and Redirect Helpers (`backend/app/core/security.py`)

- `generate_state`: random OIDC state.
- `generate_code_verifier`: PKCE code verifier.
- `challenge_from_verifier`: PKCE S256 challenge.
- `safe_return_to`: sanitizes return path to prevent open redirects.

### Redis and Sessions

- `backend/app/stores/redis_store.py`
  - `login_state_key`: Redis key namespace for one-time login states.
  - `session_key`: Redis key namespace for authenticated sessions.
  - `RedisStore.set_json` / `get_json` / `delete` / `expire`: JSON Redis primitives.
- `backend/app/services/sessions.py`
  - `create_session`: persists session payload.
  - `get_session`: reads and refreshes TTL (sliding session).
  - `delete_session`: removes session payload.

### OIDC Integration (`backend/app/services/keycloak_oidc.py`)

- `KeycloakOIDC.build_authorize_url`: constructs authorize URL (supports `register` and optional `prompt`).
- `KeycloakOIDC.exchange_code_for_tokens`: auth code -> token response.
- `KeycloakOIDC.refresh_tokens`: refresh token -> new token response.
- `KeycloakOIDC.fetch_userinfo`: reads claims from userinfo endpoint.
- `KeycloakOIDC.fetch_account_profile`: fetches current user account profile from Keycloak account endpoint.
- `KeycloakOIDC.update_web_preferences`: updates `web-prefrences` user attribute in Keycloak.
- `KeycloakOIDC.build_logout_url`: constructs RP-initiated logout URL.

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

### Dependencies, Sessions, Cookies, CSRF (`backend/app/api/deps.py`)

- `get_redis_store`: app-state Redis accessor.
- `get_user_store`: app-state app user DB store accessor.
- `set_auth_cookies`: sets `app_session` + `csrf_token`.
- `clear_auth_cookies`: clears auth cookies.
- `_csrf_from_request`: extracts cookie/header CSRF values.
- `require_csrf`: validates CSRF triplet (cookie/header/session).
- `optional_session`: resolves session from cookie (or `None`).
- `require_session`: enforces authenticated session.

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

### Application Wiring

- `backend/app/api/router.py`
  - `api_router`: aggregates `health`, `auth`, and `profile` routers.
- `backend/app/main.py`
  - `lifespan`: initializes/closes Redis, HTTP client, and app user DB store.
  - `app`: FastAPI app with CORS middleware and API router mounted.
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
