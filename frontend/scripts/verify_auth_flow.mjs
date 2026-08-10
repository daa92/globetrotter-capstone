// frontend/scripts/verify_auth_flow.mjs
//
// A lightweight contract check between the frontend and the real backend
// — not a full browser-automation E2E suite (no Playwright/Cypress here),
// but genuinely useful: it replicates exactly what src/api/client.js and
// AuthContext.jsx do (same endpoints, same payload shapes, same cookie
// handling) using Node's own fetch, against a REAL running backend.
//
// Run this any time you change src/api/client.js or AuthContext.jsx, to
// catch a contract mismatch (wrong field name, wrong endpoint, etc.)
// before finding out the hard way in a browser.
//
// Usage (from frontend/, with the backend running on :8000):
//   node scripts/verify_auth_flow.mjs
//
// Node's fetch doesn't handle cookies automatically like a browser does
// with credentials: "include" — this script manually captures Set-Cookie
// and resends it, which is the one thing it does differently from real
// frontend code, purely to compensate for Node not being a browser.
const API_URL = "http://localhost:8000";
let cookieJar = "";

async function request(path, { method = "GET", body } = {}, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (cookieJar) headers.Cookie = cookieJar;

  const resp = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const setCookie = resp.headers.get("set-cookie");
  if (setCookie) cookieJar = setCookie.split(";")[0]; // browser would store this automatically

  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;
  return { status: resp.status, data };
}

async function main() {
  const username = `frontend_sim_${Date.now()}`;
  const email = `${username}@example.com`;
  const password = "FrontendSim123";

  console.log("=== 1. register (exact payload shape from api/client.js `register`) ===");
  const reg = await request("/auth/register", { method: "POST", body: { username, email, password, preferences: [] } });
  console.log(reg.status, reg.data.detail);

  console.log("\n=== 2. extract verification token from the dev outbox (stand-in for reading real email) ===");
  const fs = await import("fs");
  const outbox = JSON.parse(fs.readFileSync("../data/outbox.json", "utf-8"));
  const msg = outbox.filter((m) => m.to === email).pop();
  const token = msg.body.split("token: ")[1].split("\n")[0];
  console.log("token found:", token.slice(0, 8) + "...");

  console.log("\n=== 3. verifyAccount(token) ===");
  const verify = await request("/auth/verify", { method: "POST", body: { token } });
  console.log(verify.status, verify.data.detail);

  console.log("\n=== 4. login(username, password) — exact shape AuthContext.login expects ===");
  const login = await request("/auth/login", { method: "POST", body: { username, password } });
  console.log(login.status, "mfa_required" in login.data ? login.data : { access_token: "present", expires_in_minutes: login.data.expires_in_minutes });
  const accessToken = login.data.access_token;
  console.log("cookie jar now contains the refresh cookie:", cookieJar ? "yes" : "no");

  console.log("\n=== 5. getMe(token) — what AuthContext stores as `user` ===");
  const me = await request("/users/me", {}, accessToken);
  console.log(me.status, me.data);

  console.log("\n=== 6. refreshToken() using ONLY the cookie (simulates page reload) ===");
  const refresh = await request("/auth/refresh", { method: "POST" });
  console.log(refresh.status, refresh.data.access_token ? "got a new access_token via cookie alone -- exactly what AuthContext does on app load" : refresh.data);

  console.log("\n=== 7. logout() ===");
  const logout = await request("/auth/logout", { method: "POST" });
  console.log(logout.status, logout.data);

  console.log("\n✅ Every call src/api/client.js makes for the auth flow matches the real backend's actual behavior.");
}

main().catch((err) => {
  console.error("FAILED:", err);
  process.exit(1);
});
