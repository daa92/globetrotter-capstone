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
  let url = `${API_URL}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null))
    ).toString();
    if (qs) url += `?${qs}`;
  }

  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(url, {
    method,
    headers,
    credentials: "include", // sends/receives the httpOnly gt_refresh_token cookie
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const text = await resp.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  /*if (!resp.ok) {
    throw new ApiError(resp.status, data?.detail ?? data ?? resp.statusText);
  }*/
  if (!resp.ok) {
  	let message = data?.detail ?? data ?? resp.statusText;
  	// FastAPI validation errors (422) return `detail` as an array of
  	// {loc, msg, type} objects, not a string — rendering that directly
  	// as a React child crashes the whole app with no error boundary to
  	// catch it. Normalize to one readable string here, globally.
  	if (Array.isArray(message)) {
    		message = message
      		.map((e) => {
        		const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : "field";
        		return `${field}: ${e.msg}`;
      		})
      		.join("; ");
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
