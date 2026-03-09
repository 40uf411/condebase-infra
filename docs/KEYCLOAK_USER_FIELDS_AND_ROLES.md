# Keycloak User Fields, Classes, Ranks, and Roles

Guide for modeling business identity data in Keycloak and exposing it to this app.

## What To Use For What

### User profile attributes

Use for structured domain metadata:

- `employee_id`
- `department`
- `team`
- `user_class`
- `rank`
- `web-prefrences` (project compatibility key)

### Groups

Use for hierarchical classification:

- `/class/mage`
- `/class/warrior`
- `/rank/gold`
- `/rank/silver`

### Roles

Use for authorization intent:

- `admin`
- `manager`
- `can_manage_users`
- `can_assign_rank`

Recommended pattern:

1. Class/rank in groups.
2. Permissions in roles.
3. Additional metadata in attributes.

## Create Custom User Attributes

In Keycloak admin:

1. Open `https://auth.local/admin`.
2. Select realm `auth_app`.
3. Go to `Realm settings -> User profile`.
4. Add attributes.
5. Configure:
   - display name
   - validators (`length`, `pattern`, `options`)
   - who can view/edit

Guidelines:

- Use stable lowercase snake_case names.
- Prefer finite option validators for controlled values.
- Keep attribute names backward compatible after release.

## Special Compatibility Attribute

This project currently expects `web-prefrences` (spelling preserved for compatibility with existing sessions/data).

If you rename it, you must update:

- `backend/app/domain/preferences.py`
- existing user data in Keycloak
- any dependent session parsing logic

## Model Class and Rank

### Option A: Groups (recommended)

1. Create groups under `/class/*` and `/rank/*`.
2. Assign one class and one rank group per user.

Why:

- hierarchy support
- clean admin filtering
- easy claim mapping via group membership mapper

### Option B: Attributes

Store class/rank as attributes (`user_class`, `rank`) when hierarchy is unnecessary.

### Option C: Roles

Use only if class/rank should also directly affect authorization checks.

## Expose Data As OIDC Claims

The backend reads claims from `userinfo` on login callback and stores them in session payload.

Configure claims:

1. `Clients -> auth-app-bff -> Client scopes`.
2. Choose `profile` or dedicated custom scope.
3. Add protocol mappers:
   - `User Attribute` for each custom attribute
   - `Group Membership` for groups
   - `Realm roles` and/or `Client roles` for roles
4. Ensure mappers are enabled for `userinfo`.

## Verify In This Project

1. Log out and log in again.
2. Open `https://app.local/profile`.
3. Inspect claim panels in UI.
4. Optional API verification:
   - `GET https://app.local/api/auth/me`
   - `GET https://app.local/api/profile`

Important:

- Claims are session-cached at login time.
- Mapper/profile changes appear only after new login.

## Troubleshooting

### Attribute missing in app

- Mapper missing or disabled on `userinfo`.
- Wrong client scope assignment.
- Session not refreshed (re-login required).

### Group claims missing

- User not assigned to expected groups.
- Group membership mapper missing.

### Role claims missing

- Role mapper missing for realm/client roles.
- Role assigned in wrong realm or wrong client.
