# Keycloak User Fields, Classes, Ranks, and Roles

This guide explains how to:

1. Add domain-specific fields to users.
2. Model classes and ranks.
3. Expose that data to this app through OIDC claims.

## What to Use for What

Use these Keycloak features intentionally:

1. User profile attributes:
For business/domain metadata, for example `employee_id`, `department`, `guild_name`, `user_class`, `rank`, `web-prefrences`.

2. Groups:
For hierarchical classification, for example `/class/mage`, `/rank/gold`.

3. Roles:
For permissions/authorization, for example `admin`, `moderator`, `can_manage_users`.

Recommended model:

1. Class and rank as groups.
2. Permissions as roles.
3. Extra metadata as user attributes.

## Add Domain-Specific User Fields

In Keycloak Admin Console (`https://auth.local/admin`):

1. Select realm `auth_app`.
2. Go to `Realm settings -> User profile`.
3. Add each custom attribute (for example `department`, `user_class`, `rank`).
4. Configure display and validation:
Set display name, optional help text, and validators (`length`, `pattern`, `options`, etc.).
5. Configure permissions:
Choose who can view/edit each field (admins only, users, or both).

Notes:

1. Attribute names should be stable and lowercase snake_case (for example `user_class`).
2. If values come from a fixed list, prefer an `options` validator.
3. The backend currently uses the attribute key `web-prefrences` (typo preserved for compatibility). Keep this exact key unless you migrate backend parsing and stored data.

## Add Classes and Ranks

### Option A: Using Groups (Recommended)

1. Go to `Groups`.
2. Create hierarchy:
`/class/warrior`, `/class/mage`, `/class/archer`, `/rank/bronze`, `/rank/silver`, `/rank/gold`.
3. Open each user and assign one class group and one rank group.

Advantages:

1. Clean hierarchy.
2. Easy filtering in admin.
3. Works well with group membership claims.

### Option B: Using Attributes

Store class/rank directly in user attributes (`user_class`, `rank`) with an `options` validator.

Advantages:

1. Simpler if you do not need hierarchy.
2. Easy to edit during profile updates.

### Option C: Using Roles

Define roles like `class_mage`, `rank_gold`.
Use this only if class/rank should also drive authorization.

## Expose Fields to the App (Claims)

This project reads user data from OIDC `userinfo` during login callback, then stores it in backend session state.

To expose custom fields:

1. Open `Clients -> auth-app-bff -> Client scopes`.
2. Choose a scope (`profile` or a dedicated custom scope).
3. Add protocol mappers:
`User Attribute` mapper for each custom field:
`user_class -> claim user_class`
`rank -> claim rank`
`department -> claim department`
4. For groups, add `Group Membership` mapper.
5. For roles, add `Realm roles` and/or `Client roles` mapper.
6. Ensure mappers are enabled for `userinfo`.

## Verify in This Project

After changing fields/groups/mappers:

1. Log out and log in again.
2. Open `https://app.local/profile`.
3. Check the `All User Claims` panel.
4. Optionally inspect:
`GET https://app.local/api/auth/me`
`GET https://app.local/api/profile`

Important:

1. Existing backend sessions cache claims from login time.
2. Mapper/profile changes do not appear until the next login.

## Suggested Conventions

1. Attributes:
`department`, `team`, `user_class`, `rank`, `web-prefrences`.
2. Groups:
`/class/*`, `/rank/*`, `/org/*`.
3. Roles:
`admin`, `manager`, `can_edit_rank`, `can_assign_class`.

## Troubleshooting

1. Field exists in Keycloak but is missing in app:
Check mapper exists and is included in `userinfo`.

2. Value changed in Keycloak but old value still shown:
Log out and log in again to refresh backend session claims.

3. Class/rank not visible as groups:
Verify user is assigned the correct groups and the group mapper is active.
