const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");
const CSRF_COOKIE_NAME = import.meta.env.VITE_CSRF_COOKIE_NAME || "csrf_token";

export function buildApiUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export function getCookieValue(name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function parseJsonIfAvailable(response) {
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return response.json();
  }
  return null;
}

function createRequestError(response, payload) {
  const detail = payload?.detail || `Request failed with status ${response.status}`;
  const error = new Error(detail);
  error.status = response.status;
  error.payload = payload;
  return error;
}

async function requestJson(path, options = {}) {
  const response = await fetch(buildApiUrl(path), {
    credentials: "include",
    ...options,
  });

  const payload = await parseJsonIfAvailable(response);

  if (!response.ok) {
    throw createRequestError(response, payload);
  }

  return payload;
}

export function fetchAuthState() {
  return requestJson("/auth/me", {
    method: "GET",
  });
}

export function fetchProfile() {
  return requestJson("/profile", {
    method: "GET",
  });
}

export function updateUserPreferences(preferences, csrfToken) {
  const token = csrfToken || getCookieValue(CSRF_COOKIE_NAME);
  return requestJson("/profile/preferences", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-CSRF-Token": token } : {}),
    },
    body: JSON.stringify(preferences),
  });
}

export async function uploadProfilePicture(file, csrfToken) {
  const token = csrfToken || getCookieValue(CSRF_COOKIE_NAME);
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(buildApiUrl("/profile/picture"), {
    method: "POST",
    credentials: "include",
    headers: token ? { "X-CSRF-Token": token } : undefined,
    body: formData,
  });

  const payload = await parseJsonIfAvailable(response);

  if (!response.ok) {
    throw createRequestError(response, payload);
  }

  return payload;
}

export function buildLoginUrl(returnTo = "/profile", forcePrompt = false) {
  const query = new URLSearchParams({ returnTo });
  if (forcePrompt) {
    query.set("prompt", "login");
  }
  return buildApiUrl(`/auth/login?${query.toString()}`);
}

export function buildRegistrationUrl(returnTo = "/profile") {
  const query = new URLSearchParams({ returnTo });
  return buildApiUrl(`/auth/register?${query.toString()}`);
}

export function startLogin(returnTo = "/profile", forcePrompt = false) {
  window.location.assign(buildLoginUrl(returnTo, forcePrompt));
}

export function startRegistration(returnTo = "/profile") {
  window.location.assign(buildRegistrationUrl(returnTo));
}

export function logout(csrfToken) {
  const token = csrfToken || getCookieValue(CSRF_COOKIE_NAME);
  return requestJson("/auth/logout", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-CSRF-Token": token } : {}),
    },
  });
}
