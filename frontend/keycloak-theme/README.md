# Keycloak Theme

This project builds the Keycloak login theme used by this repository.

## Stack

- Vite + React + TypeScript
- Keycloakify
- `@keycloakify/login-ui` (login/register and related auth pages)

## Commands

- `npm run update-kc-gen`
- `npm run build`
- `npm run build-keycloak-theme`

## Theme Entry

- Theme name: `auth-console-theme` (derived from `package.json` name).
- Login/register styling is customized in:
  - `src/login/styleLevelCustomization.tsx`
  - `public/theme-overrides.css`
- Email theme name: `auth-console-email`.
  - Files are in `custom-themes/auth-console-email/email/`.
  - The HTML email wrapper is customized in `custom-themes/auth-console-email/email/html/template.ftl`.

## Packaging

`Dockerfile.keycloak` builds this theme and injects:

- the generated login theme JAR into `/opt/keycloak/providers`
- custom email theme files into `/opt/keycloak/themes`

To use the email theme, set Realm Settings -> Themes -> Email Theme to `auth-console-email`.
