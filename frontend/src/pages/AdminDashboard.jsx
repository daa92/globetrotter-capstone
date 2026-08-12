/**
 * src/pages/AdminDashboard.jsx
 *
 * Reachable only at the unlisted path configured in AnimatedRoutes.jsx
 * (not linked from any nav/menu — see App/AnimatedRoutes). That hidden
 * URL is obscurity, not security: every request this page makes is still
 * checked server-side by get_current_admin, so a non-admin who finds the
 * URL gets 403s, not data. If `user.is_admin` isn't true, we don't even
 * attempt the calls — we just say so.
 */
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  ApiError,
  approvePayout,
  approvePlace,
  listAllFeedback,
  listPayouts,
  listPendingPlaces,
  rejectPayout,
  rejectPlace,
} from "../api/client";

const TABS = [
  { id: "payouts", label: "Payouts" },
  { id: "places", label: "Place submissions" },
  { id: "feedback", label: "Feedback" },
];

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

export default function AdminDashboard() {
  const { user, accessToken, loading } = useAuth();
  const [tab, setTab] = useState("payouts");

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
        {TABS.map((t) => (
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
    </div>
  );
}
