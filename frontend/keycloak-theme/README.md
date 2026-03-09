# Keycloak Theme

This project builds and packages the custom Keycloak login theme used by the platform.

## Stack

- Vite + React + TypeScript
- Keycloakify
- `@keycloakify/login-ui`

## Key Theme Names

- Login theme: `auth-console-theme`
- Email theme: `auth-console-email`

## Important Source Files

- `src/login/styleLevelCustomization.tsx`: login/register style overrides.
- `public/theme-overrides.css`: global CSS overrides for Keycloak pages.
- `custom-themes/auth-console-email/email/`: email theme assets.
- `custom-themes/auth-console-email/email/html/template.ftl`: HTML email wrapper.

## Commands

From `frontend/keycloak-theme/`:

```bash
npm run update-kc-gen
npm run build
npm run build-keycloak-theme
```

## Packaging

`Dockerfile.keycloak`:

1. Builds theme artifacts.
2. Copies generated login theme JAR into `/opt/keycloak/providers`.
3. Copies custom email theme files into `/opt/keycloak/themes`.

This image is consumed by `infra/docker-compose.yml` for the `keycloak` service.

## Activation In Keycloak

1. Open `https://auth.local/admin`.
2. Select realm `auth_app`.
3. Go to `Realm settings -> Themes`.
4. Set:
   - `Login Theme` = `auth-console-theme`
   - `Email Theme` = `auth-console-email` (if email theme is desired)
5. Save.

## Troubleshooting

- Theme not updating:
  - clear browser cache
  - rebuild and restart `keycloak` container
- Email styles not applied:
  - ensure `Email Theme` is set to `auth-console-email`
  - verify files are present under `/opt/keycloak/themes/auth-console-email`
