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
  listAdmins,
  listAllFeedback,
  listPayouts,
  listPendingPlaces,
  promoteAdmin,
  rejectPayout,
  rejectPlace,
  revokeAdmin,
  searchUsersForPromotion,
  updateAdminPermissions,
} from "../api/client";

const TABS = [
  { id: "payouts", label: "Payouts" },
  { id: "places", label: "Place submissions" },
  { id: "feedback", label: "Feedback" },
];

const PRINCIPAL_TAB = { id: "admins", label: "Manage admins" };

const PERMISSION_LABELS = {
  payouts: "Payouts",
  places: "Place submissions",
  feedback: "Feedback",
  notifications: "Send notifications",
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
  if (payouts.length === 0) return <p className="text-sm text-neutral-400">No pending payout requests.</p>;

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

  if (error) return <p className="text-red-500 text-sm">{error}</p>;
  if (places === null) return <p className="text-sm text-neutral-400">Loading…</p>;
  if (places.length === 0) return <p className="text-sm text-neutral-400">No pending place submissions.</p>;

  return (
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
  if (feedback.length === 0) return <p className="text-sm text-neutral-400">No feedback yet.</p>;

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
  const [tab, setTab] = useState("payouts");
  const tabs = user?.is_principal_admin ? [...TABS, PRINCIPAL_TAB] : TABS;

  if (loading) return null;

  if (!user || !user.is_admin) {
    // Deliberately generic — doesn't hint that an admin dashboard exists
    // at this path for non-admins who happen to load it.
    return (
      <div className="max-w-lg mx-auto mt-24 text-center text-neutral-400">
        <p>404 — page not found.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-xl font-semibold mb-6">Admin dashboard</h1>
      <div className="flex gap-2 mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
              tab === t.id
                ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                : "bg-neutral-100 dark:bg-neutral-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "payouts" && <PayoutsTab token={accessToken} />}
      {tab === "places" && <PlacesTab token={accessToken} />}
      {tab === "feedback" && <FeedbackTab token={accessToken} />}
      {tab === "admins" && user.is_principal_admin && <AdminsTab token={accessToken} />}
    </div>
  );
}
