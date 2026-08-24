/**
 * src/pages/AdminDashboard.jsx
 *
 * Reachable two ways: the unlisted ADMIN_PATH URL (see
 * constants/adminPath.js), and — once you're a logged-in admin — a normal
 * nav link in Navbar.jsx. Neither is the actual access control: every
 * request this page makes is still checked server-side (get_current_admin
 * / require_permission / get_current_principal_admin), so a non-admin
 * gets 403s no matter how they arrive here. If `user.is_admin` isn't
 * true, we don't even attempt the calls — we just say so.
 */
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  ADMIN_PERMISSIONS,
  ApiError,
  approvePayout,
  approvePlace,
  deleteUser,
  getSeedStatus,
  getSystemOverview,
  listAdmins,
  listAllFeedback,
  listAllUsers,
  listAuditLogs,
  listPayouts,
  listPendingPlaces,
  listSentNotifications,
  lockUser,
  promoteAdmin,
  rejectPayout,
  rejectPlace,
  revokeAdmin,
  searchUsersForPromotion,
  seedDestinations,
  sendAdminNotification,
  unlockUser,
  updateAdminPermissions,
} from "../api/client";

const TABS_CONFIG = [
  { id: "overview", label: "Overview", permission: null },
  { id: "users", label: "Users", permission: "users" },
  { id: "payouts", label: "Payouts", permission: "payouts" },
  { id: "places", label: "Place submissions", permission: "places" },
  { id: "feedback", label: "Feedback", permission: "feedback" },
  { id: "notifications", label: "Notifications", permission: "notifications" },
  { id: "logs", label: "Audit log", permission: "logs" },
];

const PRINCIPAL_TAB = { id: "admins", label: "Manage admins" };

const PERMISSION_LABELS = {
  payouts: "Payouts",
  places: "Place submissions",
  feedback: "Feedback",
  notifications: "Send notifications",
  users: "Manage users",
  logs: "View audit log",
};

function Card({ children }) {
  return (
    <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-4">
      {children}
    </div>
  );
}

function ActionButton({ onClick, tone = "neutral", children, disabled }) {
  const tones = {
    approve: "bg-emerald-600 hover:bg-emerald-700 text-white",
    reject: "bg-red-600 hover:bg-red-700 text-white",
    neutral: "bg-neutral-200 hover:bg-neutral-300 dark:bg-neutral-700 dark:hover:bg-neutral-600",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-3 py-1.5 rounded-lg text-sm font-medium disabled:opacity-50 ${tones[tone]}`}
    >
      {children}
    </button>
  );
}

function PayoutsTab({ token }) {
  const [payouts, setPayouts] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setPayouts(await listPayouts(token, "pending"));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load payouts");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (id, action) => {
    setBusyId(id);
    try {
      await (action === "approve" ? approvePayout : rejectPayout)(token, id);
      setPayouts((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  if (error) return <p className="text-red-500 text-sm">{error}</p>;
  if (payouts === null) return <p className="text-sm text-neutral-400">Loading…</p>;
  if (payouts.length === 0) return <p className="text-sm text-neutral-400">No pending payout requests yet.</p>;

  return (
    <div className="space-y-3">
      {payouts.map((p) => (
        <Card key={p.id}>
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-medium">{p.username}</p>
              <p className="text-sm text-neutral-400">
                ${p.amount_usd} · requested {new Date(p.requested_at).toLocaleString()}
              </p>
            </div>
            <div className="flex gap-2">
              <ActionButton tone="approve" disabled={busyId === p.id} onClick={() => act(p.id, "approve")}>
                Approve
              </ActionButton>
              <ActionButton tone="reject" disabled={busyId === p.id} onClick={() => act(p.id, "reject")}>
                Reject
              </ActionButton>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function SeedCatalogueCard({ token }) {
  const [status, setStatus] = useState(null); // { total_in_seed_list, already_imported, remaining }
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [log, setLog] = useState([]); // recent imported names, most recent first

  const loadStatus = useCallback(async () => {
    try {
      setError(null);
      setStatus(await getSeedStatus(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't check the starter catalogue status");
    }
  }, [token]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const runAll = async () => {
    setRunning(true);
    setError(null);
    try {
      // Keep going in small batches until nothing's left — mirrors the
      // backend's own batching (a free-tier host doesn't like one giant
      // request), but from here it just looks like one click to the admin.
      let remaining = status?.remaining ?? Infinity;
      while (remaining > 0) {
        const batch = await seedDestinations(token, 5);
        setLog((prev) => [
          ...batch.results.map((r) => `${r.status === "ok" ? "✓" : "✗"} ${r.name}`).reverse(),
          ...prev,
        ]);
        remaining = batch.remaining;
        setStatus((prev) => ({ ...prev, remaining, already_imported: (prev?.already_imported ?? 0) + batch.processed }));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Seeding stopped early — try clicking again to resume");
    } finally {
      setRunning(false);
    }
  };

  if (error && !status) return <Card><p className="text-red-500 text-sm">{error}</p></Card>;
  if (!status) return <Card><p className="text-sm text-neutral-400">Checking starter catalogue…</p></Card>;

  return (
    <Card>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <p className="font-medium">Starter destinations catalogue</p>
          <p className="text-sm text-neutral-400 mt-0.5">
            {status.already_imported} of {status.total_in_seed_list} curated Cameroon places are live.
            {status.remaining > 0 ? ` ${status.remaining} not imported yet.` : " All imported."}
          </p>
        </div>
        {status.remaining > 0 && (
          <ActionButton tone="approve" disabled={running} onClick={runAll}>
            {running ? "Seeding…" : `Seed ${status.remaining} remaining`}
          </ActionButton>
        )}
      </div>
      {error && <p className="text-red-500 text-xs mt-2">{error}</p>}
      {log.length > 0 && (
        <div className="mt-3 max-h-40 overflow-y-auto text-xs font-mono text-neutral-400 space-y-0.5">
          {log.map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      )}
    </Card>
  );
}

function PlacesTab({ token }) {
  const [places, setPlaces] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setPlaces(await listPendingPlaces(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load submissions");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (id, action) => {
    setBusyId(id);
    try {
      await (action === "approve" ? approvePlace : rejectPlace)(token, id);
      setPlaces((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <SeedCatalogueCard token={token} />

      {error && <p className="text-red-500 text-sm">{error}</p>}
      {places === null && !error && <p className="text-sm text-neutral-400">Loading…</p>}
      {places !== null && places.length === 0 && <p className="text-sm text-neutral-400">No pending place submissions. Try adding some</p>}
      {places !== null && places.length > 0 && (
        <div className="space-y-3">
          {places.map((p) => (
            <Card key={p.id}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium">
                    {p.name} <span className="text-neutral-400 font-normal">· {p.region}</span>
                  </p>
                  <p className="text-sm text-neutral-400 max-w-xl">{p.description}</p>
                  <p className="text-xs text-neutral-400 mt-1">
                    submitted by {p.submitted_by} · {new Date(p.submitted_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <ActionButton tone="approve" disabled={busyId === p.id} onClick={() => act(p.id, "approve")}>
                    Approve
                  </ActionButton>
                  <ActionButton tone="reject" disabled={busyId === p.id} onClick={() => act(p.id, "reject")}>
                    Reject
                  </ActionButton>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function FeedbackTab({ token }) {
  const [feedback, setFeedback] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setFeedback(await listAllFeedback(token));
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load feedback");
      }
    })();
  }, [token]);

  if (error) return <p className="text-red-500 text-sm">{error}</p>;
  if (feedback === null) return <p className="text-sm text-neutral-400">Loading…</p>;
  if (feedback.length === 0) return <p className="text-sm text-neutral-400">No feedback for now.</p>;

  return (
    <div className="space-y-3">
      {feedback.map((f) => (
        <Card key={f.id}>
          <div className="flex items-center justify-between">
            <p className="font-medium">{f.username}</p>
            {f.rating != null && <p className="text-sm text-neutral-400">Rating: {f.rating}/5</p>}
          </div>
          {f.message && <p className="text-sm mt-1">{f.message}</p>}
          <p className="text-xs text-neutral-400 mt-1">{new Date(f.submitted_at).toLocaleString()}</p>
        </Card>
      ))}
    </div>
  );
}

function StatCard({ label, value, tone }) {
  const tones = {
    neutral: "",
    warn: "text-amber-600 dark:text-amber-400",
    danger: "text-red-600 dark:text-red-400",
  };
  return (
    <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-4">
      <p className="text-xs text-neutral-400 mb-1">{label}</p>
      <p className={`text-2xl font-semibold ${tones[tone] || ""}`}>{value}</p>
    </div>
  );
}

function OverviewTab({ token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setData(await getSystemOverview(token));
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load system overview");
      }
    })();
  }, [token]);

  if (error) return <p className="text-red-500 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-neutral-400">Loading…</p>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total users" value={data.total_users} />
        <StatCard label="Verified" value={data.verified_users} />
        <StatCard label="Unverified" value={data.unverified_users} tone={data.unverified_users > 0 ? "warn" : "neutral"} />
        <StatCard label="Locked" value={data.locked_users} tone={data.locked_users > 0 ? "danger" : "neutral"} />
        <StatCard label="Admins" value={data.total_admins} />
        <StatCard label="New signups (7d)" value={data.new_registrations_last_7d} />
        <StatCard label="Notifications sent (7d)" value={data.notifications_sent_last_7d} />
        <StatCard label="Pending payouts" value={data.pending_payouts} tone={data.pending_payouts > 0 ? "warn" : "neutral"} />
        <StatCard label="Payouts approved (total)" value={`$${data.approved_payouts_total_usd}`} />
        <StatCard label="Pending place submissions" value={data.pending_place_submissions} tone={data.pending_place_submissions > 0 ? "warn" : "neutral"} />
        <StatCard label="Total feedback" value={data.total_feedback} />
        <StatCard label="Avg. feedback rating" value={data.average_feedback_rating ?? "—"} />
      </div>

      <div>
        <p className="font-medium mb-2">Background jobs</p>
        <div className="space-y-2">
          {data.background_jobs.map((job) => (
            <Card key={job.name}>
              <p className="font-medium text-sm">{job.name}</p>
              <p className="text-xs text-neutral-400 mt-1">{job.description}</p>
              <p className="text-xs mt-2">
                Runs every {job.interval_seconds}s · TTL {job.ttl_minutes}min · ran {job.run_count} time(s)
                {job.last_run_at && <> · last run {new Date(job.last_run_at).toLocaleString()}</>}
                {job.last_run_at && <> · purged {job.last_run_purged_count} last run</>}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function UserRow({ u, token, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const doLock = async () => {
    const reason = window.prompt(`Lock ${u.username}? Optional reason:`, "");
    if (reason === null) return;
    setBusy(true);
    setError(null);
    try {
      await lockUser(token, u.username, reason || undefined);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to lock user");
      setBusy(false);
    }
  };

  const doUnlock = async () => {
    setBusy(true);
    setError(null);
    try {
      await unlockUser(token, u.username);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to unlock user");
      setBusy(false);
    }
  };

  const doDelete = async () => {
    if (!window.confirm(`Permanently delete ${u.username}? This cannot be undone.`)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteUser(token, u.username);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to delete user");
      setBusy(false);
    }
  };

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-medium">
            {u.username}
            {u.is_admin && (
              <span className="ml-2 text-xs font-semibold text-blue-600 dark:text-blue-400">
                {u.is_principal_admin ? "PRINCIPAL ADMIN" : "ADMIN"}
              </span>
            )}
            {!u.is_verified && (
              <span className="ml-2 text-xs font-semibold text-amber-600 dark:text-amber-400">UNVERIFIED</span>
            )}
            {u.is_locked && (
              <span className="ml-2 text-xs font-semibold text-red-600 dark:text-red-400">LOCKED</span>
            )}
          </p>
          {u.email && <p className="text-xs text-neutral-400">{u.email}</p>}
          {u.phone && <p className="text-xs text-neutral-400">{u.phone}</p>}
          <p className="text-xs text-neutral-400 mt-1">
            joined {new Date(u.created_at).toLocaleDateString()} · ref {u.referral_code}
            {u.mfa_enabled && " · MFA on"}
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          {u.is_locked ? (
            <ActionButton tone="approve" disabled={busy} onClick={doUnlock}>
              Unlock
            </ActionButton>
          ) : (
            <ActionButton tone="reject" disabled={busy} onClick={doLock}>
              Lock
            </ActionButton>
          )}
          <ActionButton tone="reject" disabled={busy} onClick={doDelete}>
            Delete
          </ActionButton>
        </div>
      </div>
      {error && <p className="text-red-500 text-xs mt-2">{error}</p>}
    </Card>
  );
}

function UsersTab({ token }) {
  const [users, setUsers] = useState(null);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [verifiedFilter, setVerifiedFilter] = useState("all"); // all | verified | unverified
  const [lockedFilter, setLockedFilter] = useState("all"); // all | locked | unlocked

  const load = useCallback(async () => {
    try {
      setError(null);
      const filters = {};
      if (search.trim()) filters.q = search.trim();
      if (verifiedFilter !== "all") filters.verified = verifiedFilter === "verified";
      if (lockedFilter !== "all") filters.locked = lockedFilter === "locked";
      setUsers(await listAllUsers(token, filters));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load users");
    }
  }, [token, search, verifiedFilter, lockedFilter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Search username or email…"
            className="flex-1 min-w-[180px] rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
          />
          <select
            value={verifiedFilter}
            onChange={(e) => setVerifiedFilter(e.target.value)}
            className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-2 py-1.5 text-sm"
          >
            <option value="all">All verification</option>
            <option value="verified">Verified</option>
            <option value="unverified">Unverified</option>
          </select>
          <select
            value={lockedFilter}
            onChange={(e) => setLockedFilter(e.target.value)}
            className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-2 py-1.5 text-sm"
          >
            <option value="all">All lock status</option>
            <option value="locked">Locked</option>
            <option value="unlocked">Not locked</option>
          </select>
          <ActionButton tone="neutral" onClick={load}>
            Apply
          </ActionButton>
        </div>
      </Card>

      {error && <p className="text-red-500 text-sm">{error}</p>}
      {users === null && !error && <p className="text-sm text-neutral-400">Loading…</p>}
      {users !== null && users.length === 0 && <p className="text-sm text-neutral-400">No matching users.</p>}
      {users !== null && (
        <div className="space-y-3">
          {users.map((u) => (
            <UserRow key={u.username} u={u} token={token} onChanged={load} />
          ))}
        </div>
      )}
    </div>
  );
}

function NotificationComposer({ token, onSent }) {
  const [mode, setMode] = useState("unicast"); // unicast | multicast | broadcast
  const [usernamesInput, setUsernamesInput] = useState("");
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [alsoEmail, setAlsoEmail] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const payload = { title, message, also_email: alsoEmail, broadcast: mode === "broadcast" };
      if (mode !== "broadcast") {
        const usernames = usernamesInput
          .split(",")
          .map((u) => u.trim())
          .filter(Boolean);
        if (mode === "unicast" && usernames.length !== 1) {
          throw new ApiError(400, "Unicast needs exactly one username");
        }
        payload.usernames = usernames;
      }
      const res = await sendAdminNotification(token, payload);
      setResult(res);
      setTitle("");
      setMessage("");
      setUsernamesInput("");
      onSent();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to send notification");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <p className="font-medium mb-3">Send a/some notification(s)</p>
      <form onSubmit={submit} className="space-y-3">
        <div className="flex gap-4 text-sm">
          {["unicast", "multicast", "broadcast"].map((m) => (
            <label key={m} className="flex items-center gap-1.5 cursor-pointer">
              <input type="radio" checked={mode === m} onChange={() => setMode(m)} />
              {m === "unicast" ? "One user" : m === "multicast" ? "Several users" : "Everyone (broadcast)"}
            </label>
          ))}
        </div>

        {mode !== "broadcast" && (
          <input
            value={usernamesInput}
            onChange={(e) => setUsernamesInput(e.target.value)}
            placeholder={mode === "unicast" ? "username" : "username1, username2, username3…"}
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
          />
        )}

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          maxLength={150}
          required
          className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
        />
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Message"
          maxLength={2000}
          required
          rows={3}
          className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
        />
        <label className="flex items-center gap-1.5 text-sm cursor-pointer">
          <input type="checkbox" checked={alsoEmail} onChange={(e) => setAlsoEmail(e.target.checked)} />
          Also send via Email box (if the recipient has one on file)
        </label>

        <ActionButton tone="approve" disabled={busy}>
          {busy ? "Sending…" : "Send"}
        </ActionButton>
      </form>

      {error && <p className="text-red-500 text-xs mt-2">{error}</p>}
      {result && (
        <p className="text-emerald-600 dark:text-emerald-400 text-xs mt-2">
          Sent to {result.notified} recipient(s){result.emailed > 0 && `, emailed ${result.emailed}`}.
        </p>
      )}
    </Card>
  );
}

function NotificationsTab({ token }) {
  const [sent, setSent] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setSent(await listSentNotifications(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load notification history");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <NotificationComposer token={token} onSent={load} />

      <div>
        <p className="font-medium mb-2">Sent history</p>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {sent === null && !error && <p className="text-sm text-neutral-400">Loading…</p>}
        {sent !== null && sent.length === 0 && <p className="text-sm text-neutral-400">Nothing sent yet.</p>}
        {sent !== null && (
          <div className="space-y-2">
            {sent.map((b) => (
              <Card key={b.id}>
                <div className="flex items-center justify-between">
                  <p className="font-medium text-sm">{b.title}</p>
                  <span className="text-xs uppercase text-neutral-400">{b.audience}</span>
                </div>
                <p className="text-sm mt-1">{b.message}</p>
                <p className="text-xs text-neutral-400 mt-1">
                  {b.recipient_count} recipient(s) · sent by {b.sent_by} · {new Date(b.created_at).toLocaleString()}
                  {b.also_email && ` · emailed ${b.emailed_count}`}
                </p>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function LogsTab({ token }) {
  const [logs, setLogs] = useState(null);
  const [error, setError] = useState(null);
  const [actionFilter, setActionFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");

  const load = useCallback(async () => {
    try {
      setError(null);
      const filters = {};
      if (actionFilter.trim()) filters.action = actionFilter.trim();
      if (actorFilter.trim()) filters.actor = actorFilter.trim();
      if (targetFilter.trim()) filters.target = targetFilter.trim();
      setLogs(await listAuditLogs(token, filters));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load audit log");
    }
  }, [token, actionFilter, actorFilter, targetFilter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap gap-2">
          <input
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Action (e.g. user.locked)"
            className="flex-1 min-w-[140px] rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
          />
          <input
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Actor"
            className="flex-1 min-w-[140px] rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
          />
          <input
            value={targetFilter}
            onChange={(e) => setTargetFilter(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Target"
            className="flex-1 min-w-[140px] rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
          />
          <ActionButton tone="neutral" onClick={load}>
            Apply
          </ActionButton>
        </div>
      </Card>

      {error && <p className="text-red-500 text-sm">{error}</p>}
      {logs === null && !error && <p className="text-sm text-neutral-400">Loading…</p>}
      {logs !== null && logs.length === 0 && <p className="text-sm text-neutral-400">No matching log entries.</p>}
      {logs !== null && logs.length > 0 && (
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-neutral-100 dark:bg-neutral-800 text-left">
              <tr>
                <th className="px-3 py-2 font-medium">When</th>
                <th className="px-3 py-2 font-medium">Actor</th>
                <th className="px-3 py-2 font-medium">Action</th>
                <th className="px-3 py-2 font-medium">Target</th>
                <th className="px-3 py-2 font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-t border-neutral-200 dark:border-neutral-700">
                  <td className="px-3 py-2 whitespace-nowrap text-xs text-neutral-400">
                    {new Date(l.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">{l.actor}</td>
                  <td className="px-3 py-2 font-mono text-xs">{l.action}</td>
                  <td className="px-3 py-2">{l.target || "—"}</td>
                  <td className="px-3 py-2 text-neutral-400">{l.details || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PermissionCheckboxes({ selected, onToggle, disabled }) {
  return (
    <div className="flex flex-wrap gap-3">
      {ADMIN_PERMISSIONS.map((perm) => (
        <label
          key={perm}
          className={`flex items-center gap-1.5 text-sm ${disabled ? "opacity-50" : "cursor-pointer"}`}
        >
          <input
            type="checkbox"
            checked={selected.includes(perm)}
            disabled={disabled}
            onChange={() => onToggle(perm)}
            className="rounded"
          />
          {PERMISSION_LABELS[perm] ?? perm}
        </label>
      ))}
    </div>
  );
}

function AdminRow({ admin, token, onChanged }) {
  const [permissions, setPermissions] = useState(admin.admin_permissions);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const dirty = JSON.stringify([...permissions].sort()) !== JSON.stringify([...admin.admin_permissions].sort());

  const togglePermission = (perm) => {
    setPermissions((prev) => (prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm]));
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await updateAdminPermissions(token, admin.username, permissions);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to update permissions");
    } finally {
      setSaving(false);
    }
  };

  const revoke = async () => {
    if (!window.confirm(`Revoke admin access for ${admin.username}?`)) return;
    setSaving(true);
    setError(null);
    try {
      await revokeAdmin(token, admin.username);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to revoke admin");
      setSaving(false);
    }
  };

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-medium">
            {admin.username}
            {admin.is_principal_admin && (
              <span className="ml-2 text-xs font-semibold text-amber-600 dark:text-amber-400">
                PRINCIPAL ADMIN
              </span>
            )}
          </p>
          {admin.email && <p className="text-xs text-neutral-400">{admin.email}</p>}
        </div>
        {!admin.is_principal_admin && (
          <ActionButton tone="reject" disabled={saving} onClick={revoke}>
            Revoke
          </ActionButton>
        )}
      </div>

      <div className="mt-3">
        {admin.is_principal_admin ? (
          <p className="text-sm text-neutral-400">Implicitly has every privilege.</p>
        ) : (
          <PermissionCheckboxes selected={permissions} onToggle={togglePermission} disabled={saving} />
        )}
      </div>

      {error && <p className="text-red-500 text-xs mt-2">{error}</p>}

      {!admin.is_principal_admin && dirty && (
        <div className="mt-3">
          <ActionButton tone="approve" disabled={saving} onClick={save}>
            {saving ? "Saving…" : "Save permissions"}
          </ActionButton>
        </div>
      )}
    </Card>
  );
}

function PromoteAdminForm({ token, onPromoted }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [target, setTarget] = useState(null); // { username } once picked from results
  const [permissions, setPermissions] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const runSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    setTarget(null);
    try {
      const found = await searchUsersForPromotion(token, query.trim());
      setResults(found.filter((u) => !u.is_admin));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const togglePermission = (perm) => {
    setPermissions((prev) => (prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm]));
  };

  const confirmPromote = async () => {
    setBusy(true);
    setError(null);
    try {
      await promoteAdmin(token, target.username, permissions);
      setQuery("");
      setResults(null);
      setTarget(null);
      setPermissions([]);
      onPromoted();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to promote user");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <p className="font-medium mb-3">Promote a user to admin</p>
      <form onSubmit={runSearch} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by username…"
          className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
        />
        <ActionButton tone="neutral" disabled={searching}>
          {searching ? "Searching…" : "Search"}
        </ActionButton>
      </form>

      {results !== null && results.length === 0 && (
        <p className="text-sm text-neutral-400 mt-3">No matching non-admin users found.</p>
      )}

      {results !== null && results.length > 0 && !target && (
        <div className="mt-3 space-y-2">
          {results.map((u) => (
            <div key={u.username} className="flex items-center justify-between text-sm">
              <span>
                {u.username} {u.email && <span className="text-neutral-400">· {u.email}</span>}
              </span>
              <ActionButton tone="neutral" onClick={() => setTarget(u)}>
                Select
              </ActionButton>
            </div>
          ))}
        </div>
      )}

      {target && (
        <div className="mt-4 border-t border-neutral-200 dark:border-neutral-700 pt-3">
          <p className="text-sm mb-2">
            Grant <span className="font-medium">{target.username}</span> access to:
          </p>
          <PermissionCheckboxes selected={permissions} onToggle={togglePermission} disabled={busy} />
          <div className="flex gap-2 mt-3">
            <ActionButton tone="approve" disabled={busy} onClick={confirmPromote}>
              {busy ? "Promoting…" : "Promote to admin"}
            </ActionButton>
            <ActionButton tone="neutral" disabled={busy} onClick={() => setTarget(null)}>
              Cancel
            </ActionButton>
          </div>
        </div>
      )}

      {error && <p className="text-red-500 text-xs mt-3">{error}</p>}
    </Card>
  );
}

function AdminsTab({ token }) {
  const [admins, setAdmins] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setAdmins(await listAdmins(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load admins");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <PromoteAdminForm token={token} onPromoted={load} />

      {error && <p className="text-red-500 text-sm">{error}</p>}
      {admins === null && !error && <p className="text-sm text-neutral-400">Loading…</p>}
      {admins !== null && (
        <div className="space-y-3">
          {admins.map((a) => (
            <AdminRow key={a.username} admin={a} token={token} onChanged={load} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AdminDashboard() {
  const { user, accessToken, loading } = useAuth();
  const [tab, setTab] = useState("overview");

  if (loading) return null;

  if (!user || !user.is_admin) {
    // Deliberately generic — doesn't hint that an admin dashboard exists
    // at this path for non-admins who happen to load it.
    return (
      <div className="max-w-lg mx-auto mt-24 text-center text-neutral-400">
        <p>404  page not found.</p>
      </div>
    );
  }

  const canSee = (permission) => !permission || user.is_principal_admin || (user.admin_permissions || []).includes(permission);
  const tabs = TABS_CONFIG.filter((t) => canSee(t.permission));
  if (user.is_principal_admin) tabs.push(PRINCIPAL_TAB);
  const activeTab = tabs.some((t) => t.id === tab) ? tab : tabs[0]?.id;

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <h1 className="text-xl font-semibold mb-6">Admin dashboard</h1>
      <div className="flex flex-wrap gap-2 mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
              activeTab === t.id
                ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                : "bg-neutral-100 dark:bg-neutral-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && <OverviewTab token={accessToken} />}
      {activeTab === "users" && <UsersTab token={accessToken} />}
      {activeTab === "payouts" && <PayoutsTab token={accessToken} />}
      {activeTab === "places" && <PlacesTab token={accessToken} />}
      {activeTab === "feedback" && <FeedbackTab token={accessToken} />}
      {activeTab === "notifications" && <NotificationsTab token={accessToken} />}
      {activeTab === "logs" && <LogsTab token={accessToken} />}
      {activeTab === "admins" && user.is_principal_admin && <AdminsTab token={accessToken} />}
    </div>
  );
}
