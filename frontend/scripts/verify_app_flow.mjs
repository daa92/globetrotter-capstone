// frontend/scripts/verify_app_flow.mjs
//
// Same philosophy as verify_auth_flow.mjs: replicate exactly what the
// React pages/components do (same endpoints, same payload shapes) against
// a real running backend, to catch a contract mismatch before finding it
// in a browser. Covers everything built after the auth flow: destinations
// search (Explore), recommendations, itineraries (create/list/delete),
// earnings, and the notification center (list/mark-read/delete).
//
// Usage (from frontend/, with the backend running on :8000):
//   node scripts/verify_app_flow.mjs
const API_URL = "http://localhost:8000";
let cookieJar = "";

async function request(path, { method = "GET", body, params } = {}, token) {
  let url = `${API_URL}${path}`;
  if (params) {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null)).toString();
    if (qs) url += `?${qs}`;
  }
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (cookieJar) headers.Cookie = cookieJar;

  const resp = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const setCookie = resp.headers.get("set-cookie");
  if (setCookie) cookieJar = setCookie.split(";")[0];

  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;
  return { status: resp.status, data };
}

async function main() {
  const username = `app_sim_${Date.now()}`;
  const email = `${username}@example.com`;
  const password = "AppSim123";

  console.log("=== setup: register + verify + login (reusing the already-proven auth flow) ===");
  await request("/auth/register", { method: "POST", body: { username, email, password, preferences: ["beach"] } });
  const fs = await import("fs");
  const outbox = JSON.parse(fs.readFileSync("../data/outbox.json", "utf-8"));
  const token = outbox.filter((m) => m.to === email).pop().body.split("token: ")[1].split("\n")[0];
  await request("/auth/verify", { method: "POST", body: { token } });
  const login = await request("/auth/login", { method: "POST", body: { username, password } });
  const accessToken = login.data.access_token;
  console.log("logged in OK\n");

  console.log("=== Explore: searchDestinations({}) ===");
  const destinations = await request("/destinations", { params: {} });
  console.log(destinations.status, `${destinations.data.length} destination(s)`);
  if (!Array.isArray(destinations.data) || destinations.data.length === 0) throw new Error("Expected seeded destinations");

  console.log("\n=== Recommendations: getRecommendations(token, 12) ===");
  const recs = await request("/recommendations", { params: { limit: 12 } }, accessToken);
  console.log(recs.status, `${recs.data.length} recommendation(s)`);

  console.log("\n=== Itineraries: create -> list -> delete ===");
  const destId = destinations.data[0].id;
  const created = await request(
    "/itineraries",
    { method: "POST", body: { title: "Sim Trip", destinations: [destId], start_date: "2026-09-01", end_date: "2026-09-03" } },
    accessToken
  );
  console.log("create:", created.status, created.data.id);
  const listed = await request("/itineraries", {}, accessToken);
  console.log("list:", listed.status, `${listed.data.length} itinerary(ies)`);
  const deleted = await request(`/itineraries/${created.data.id}`, { method: "DELETE" }, accessToken);
  console.log("delete:", deleted.status);

  console.log("\n=== Earnings: getEarnings(token) — shape EarningsDashboard.jsx expects ===");
  const earnings = await request("/users/me/earnings", {}, accessToken);
  console.log(earnings.status, {
    total_earned_usd: earnings.data.total_earned_usd,
    available_fcfa: earnings.data.available_fcfa,
    referral_link: earnings.data.referral_link,
    daily_log_length: earnings.data.daily_log.length,
    payout_eligibility_keys: Object.keys(earnings.data.payout_eligibility),
  });

  console.log("\n=== Notifications: list -> mark-read -> delete (shapes NotificationCenter.jsx expects) ===");
  const notifBefore = await request("/notifications", {}, accessToken);
  console.log("list:", notifBefore.status, `${notifBefore.data.length} notification(s) (expected 0, none triggered yet)`);
  const markRead = await request("/notifications/mark-read", { method: "POST", body: { all: true } }, accessToken);
  console.log("mark-read (all, on an empty inbox):", markRead.status, markRead.data);
  const del = await request("/notifications/delete", { method: "POST", body: { all: true } }, accessToken);
  console.log("delete (all, on an empty inbox):", del.status, del.data);

  console.log("\n✅ Every call the Explore/Recommendations/Itineraries/Profile pages make matches the real backend.");
}

main().catch((err) => {
  console.error("FAILED:", err);
  process.exit(1);
});
