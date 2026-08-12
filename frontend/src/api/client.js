/**
 * src/api/client.js
 *
 * Every network call to the GT backend goes through here — nothing else
 * in the frontend should call `fetch` directly. Two things this buys us:
 *   1. One place to add the httpOnly-cookie-friendly `credentials: "include"`
 *      (required so the browser sends/receives the refresh-token cookie),
 *      and one place to attach the Authorization header.
 *   2. One consistent error shape (ApiError) instead of every component
 *      re-parsing fetch's awkward error handling.
 *
 * The access token itself is deliberately never persisted here (no
 * localStorage/sessionStorage) — it's held in React state by AuthContext
 * and re-obtained via a silent /auth/refresh call (using the httpOnly
 * cookie) on page load. This mirrors the CLI's security posture: the
 * long-lived credential (refresh token) never touches JS-readable storage.
 */

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, { method = "GET", body, token, params } = {}) {
  const url = new URL(path, API_URL);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }

  const headers = new Headers({
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  });

  const resp = await fetch(url.toString(), {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "include",
  });

  // Try to parse JSON, but don't crash if there's no JSON body or parsing fails.
  let data = null;
  try {
    // Only attempt to parse if there is a body (some endpoints return 204 No Content)
    const text = await resp.text();
    data = text ? JSON.parse(text) : null;
  } catch (e) {
    // Keep data as null — we'll fall back to resp.statusText where needed.
  }

  if (!resp.ok) {
    // Prefer explicit data.detail or data, but fall back to statusText.
    let message = (data && (data.detail ?? data)) ?? resp.statusText ?? `HTTP ${resp.status}`;

    // FastAPI validation errors (422) often return `detail` as an array of
    // { loc, msg, type } objects. Rendering that array directly inside React
    // can crash the app. Normalize arrays to a single readable string here.
    if (Array.isArray(message)) {
      message = message
        .map((e) => {
          const field =
            Array.isArray(e.loc) && e.loc.length > 0
              ? e.loc[e.loc.length - 1]
              : e.loc ?? "field";
          return `${field}: ${e.msg}`;
        })
        .join("; ");
    } else if (typeof message === "object") {
      // If message is an object (not an array), fallback to a concise string.
      // Avoid printing raw objects into the UI — stringify only as last resort.
      try {
        message = JSON.stringify(message);
      } catch {
        message = resp.statusText ?? `HTTP ${resp.status}`;
      }
    } else {
      // Ensure we have a string for the message
      message = String(message);
    }

    throw new ApiError(resp.status, message);
  }

  return data;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const register = (payload) => request("/auth/register", { method: "POST", body: payload });
export const registerPhone = (payload) => request("/auth/register/phone", { method: "POST", body: payload });
export const verifyAccount = (token) => request("/auth/verify", { method: "POST", body: { token } });

export const login = (username, password, mfa_code) =>
  request("/auth/login", { method: "POST", body: { username, password, ...(mfa_code ? { mfa_code } : {}) } });

export const loginGoogle = (id_token, mfa_code) =>
  request("/auth/google", { method: "POST", body: { id_token, ...(mfa_code ? { mfa_code } : {}) } });

export const refreshToken = () => request("/auth/refresh", { method: "POST" });
export const logout = () => request("/auth/logout", { method: "POST" });

export const requestPasswordReset = (username) =>
  request("/auth/password-reset/request", { method: "POST", body: { username } });
export const confirmPasswordReset = (token, new_password) =>
  request("/auth/password-reset/confirm", { method: "POST", body: { token, new_password } });

// ---------------------------------------------------------------------------
// Users / profile
// ---------------------------------------------------------------------------

export const getMe = (token) => request("/users/me", { token });
export const updateMe = (token, payload) => request("/users/me", { method: "PATCH", token, body: payload });
export const deleteMe = (token) => request("/users/me", { method: "DELETE", token });

// ---------------------------------------------------------------------------
// Destinations / recommendations
// ---------------------------------------------------------------------------

export const searchDestinations = (params) => request("/destinations", { params });
export const getRecommendations = (token, limit) => request("/recommendations", { token, params: { limit } });
export const getPoiCategories = () => request("/geo/poi-categories");
export const searchPois = (category, lat, lon, radius_m) =>
  request("/geo/poi", { params: { category, lat, lon, radius_m } });
export const getPlaceSummary = (name, lang) => request("/geo/place-summary", { params: { name, lang } });

// ---------------------------------------------------------------------------
// Itineraries
// ---------------------------------------------------------------------------

export const createItinerary = (token, payload) => request("/itineraries", { method: "POST", token, body: payload });
export const listItineraries = (token) => request("/itineraries", { token });
export const deleteItinerary = (token, id) => request(`/itineraries/${id}`, { method: "DELETE", token });

// ---------------------------------------------------------------------------
// Earnings / notifications (used by the profile portal, later pass)
// ---------------------------------------------------------------------------

export const getEarnings = (token) => request("/users/me/earnings", { token });
export const requestPayout = (token) => request("/users/me/payouts/request", { method: "POST", token });
export const sendHeartbeat = (token, elapsed_seconds) =>
  request("/users/me/activity/heartbeat", { method: "POST", token, body: { elapsed_seconds } });
export const listNotifications = (token, unread_only) =>
  request("/notifications", { token, params: { unread_only } });
export const unreadNotificationCount = (token) => request("/notifications/unread-count", { token });
export const markNotificationsRead = (token, body) =>
  request("/notifications/mark-read", { method: "POST", token, body });
export const deleteNotifications = (token, body) =>
  request("/notifications/delete", { method: "POST", token, body });
export const deleteNotification = (token, id) => request(`/notifications/${id}`, { method: "DELETE", token });

// ---------------------------------------------------------------------------
// Admin (hidden dashboard — every call still enforced server-side by
// get_current_admin; the frontend route being unlinked is just obscurity,
// not the actual access control)
// ---------------------------------------------------------------------------

export const bootstrapAdmin = (username, secret) =>
  request("/auth/admin/bootstrap", { method: "POST", body: { username, secret } });

export const listPayouts = (token, status_filter = "pending") =>
  request("/admin/payouts", { token, params: { status_filter } });
export const approvePayout = (token, id) =>
  request(`/admin/payouts/${id}/approve`, { method: "POST", token });
export const rejectPayout = (token, id) =>
  request(`/admin/payouts/${id}/reject`, { method: "POST", token });

export const listPendingPlaces = (token) => request("/places/pending", { token });
export const approvePlace = (token, id) => request(`/places/${id}/approve`, { method: "POST", token });
export const rejectPlace = (token, id) => request(`/places/${id}/reject`, { method: "POST", token });

export const listAllFeedback = (token) => request("/feedback", { token });
