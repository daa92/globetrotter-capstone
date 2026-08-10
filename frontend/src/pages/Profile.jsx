import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { updateMe, deleteMe, ApiError } from "../api/client";
import EarningsDashboard from "../components/profile/EarningsDashboard";
import NotificationCenter from "../components/notifications/NotificationCenter";

function OverviewTab() {
  const { t } = useTranslation();
  const { user, accessToken, refreshUser, logout } = useAuth();
  const navigate = useNavigate();

  const [preferences, setPreferences] = useState(user.preferences.join(", "));
  const [profilePictureUrl, setProfilePictureUrl] = useState(user.profile_picture_url || "");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await updateMe(accessToken, {
        preferences: preferences.split(",").map((p) => p.trim()).filter(Boolean),
        profile_picture_url: profilePictureUrl || null,
      });
      await refreshUser();
      setMessage(t("profile.profileUpdated"));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("profile.updateError"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMe(accessToken);
      await logout();
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("profile.deleteError"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-neutral-400">{t("profile.username")}</p>
            <p className="font-medium">{user.username}</p>
          </div>
          {user.email && (
            <div>
              <p className="text-neutral-400">{t("profile.email")}</p>
              <p className="font-medium">{user.email}</p>
            </div>
          )}
          {user.phone && (
            <div>
              <p className="text-neutral-400">{t("profile.phone")}</p>
              <p className="font-medium">{user.phone}</p>
            </div>
          )}
          <div>
            <p className="text-neutral-400">{t("profile.verified")}</p>
            <p className="font-medium">{user.is_verified ? t("profile.yes") : t("profile.no")}</p>
          </div>
          <div>
            <p className="text-neutral-400">{t("profile.mfa")}</p>
            <p className="font-medium">{user.mfa_enabled ? t("profile.enabled") : t("profile.disabled")}</p>
          </div>
          <div>
            <p className="text-neutral-400">{t("profile.memberSince")}</p>
            <p className="font-medium">{new Date(user.created_at).toLocaleDateString()}</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSave} className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5 space-y-4">
        <h2 className="font-semibold">{t("profile.editProfile")}</h2>

        {message && <p className="text-sm text-teal-600 dark:text-teal-400">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        <div>
          <label htmlFor="profile-preferences" className="text-sm font-medium">{t("profile.preferences")}</label>
          <input
            id="profile-preferences"
            type="text"
            value={preferences}
            onChange={(e) => setPreferences(e.target.value)}
            placeholder="beach, hiking, culture"
            className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
          />
        </div>
        <div>
          <label htmlFor="profile-picture-url" className="text-sm font-medium">{t("profile.profilePictureUrl")}</label>
          <input
            id="profile-picture-url"
            type="url"
            value={profilePictureUrl}
            onChange={(e) => setProfilePictureUrl(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg px-6 py-2 font-semibold text-white transition disabled:opacity-50"
          style={{ backgroundColor: "#127C71" }}
        >
          {saving ? t("profile.saving") : t("profile.saveChanges")}
        </button>
      </form>

      <div className="rounded-2xl border border-red-200 dark:border-red-900 p-5">
        <h2 className="font-semibold text-red-700 dark:text-red-400">{t("profile.deleteAccountTitle")}</h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{t("profile.deleteAccountBody")}</p>
        {confirmDelete ? (
          <div className="mt-3 flex gap-2">
            <button onClick={handleDelete} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white">
              {t("profile.deleteConfirm")}
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="rounded-lg border border-neutral-300 dark:border-neutral-600 px-4 py-2 text-sm"
            >
              {t("profile.cancel")}
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            className="mt-3 rounded-lg border border-red-300 dark:border-red-800 px-4 py-2 text-sm font-semibold text-red-700 dark:text-red-400"
          >
            {t("profile.deleteAccountBtn")}
          </button>
        )}
      </div>
    </div>
  );
}

export default function Profile() {
  const { t } = useTranslation();
  const { user, accessToken, isAuthenticated, loading } = useAuth();
  const [activeTab, setActiveTab] = useState("Overview");

  const TABS = [
    { key: "Overview", label: t("profile.tabOverview") },
    { key: "Earnings", label: t("profile.tabEarnings") },
    { key: "Notifications", label: t("profile.tabNotifications") },
  ];

  if (!loading && !isAuthenticated) {
    return (
      <section className="mx-auto max-w-md px-6 py-24 text-center">
        <h1 className="text-2xl font-bold">{t("profile.portalTitle")}</h1>
        <p className="mt-2 text-neutral-500 dark:text-neutral-400">{t("profile.portalBody")}</p>
        <Link
          to="/login"
          className="mt-6 inline-block rounded-full px-6 py-2 font-semibold text-white transition"
          style={{ backgroundColor: "#127C71" }}
        >
          {t("profile.login")}
        </Link>
      </section>
    );
  }

  if (loading || !user) return <div className="px-6 py-24 text-center text-neutral-400">{t("profile.loading")}</div>;

  return (
    <section className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold">{t("profile.hi", { username: user.username })}</h1>

      <div className="mt-6 flex gap-1 border-b border-neutral-200 dark:border-neutral-700">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.key
                ? "border-b-2 text-neutral-900 dark:text-white"
                : "text-neutral-400 hover:text-neutral-600"
            }`}
            style={activeTab === tab.key ? { borderColor: "#127C71" } : {}}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {activeTab === "Overview" && <OverviewTab />}
        {activeTab === "Earnings" && <EarningsDashboard accessToken={accessToken} />}
        {activeTab === "Notifications" && <NotificationCenter accessToken={accessToken} />}
      </div>
    </section>
  );
}
