import { useRef, useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { updateMe, deleteMe, uploadProfilePicture, ApiError } from "../api/client";
import EarningsDashboard from "../components/profile/EarningsDashboard";
import NotificationCenter from "../components/notifications/NotificationCenter";

function AvatarUploader({ user, accessToken, onUploaded }) {
  const { t } = useTranslation();
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const { profile_picture_url } = await uploadProfilePicture(accessToken, file);
      await onUploaded(profile_picture_url);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("profile.updateError"));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="flex items-center gap-4">
      <div
        className="h-20 w-20 shrink-0 overflow-hidden rounded-full border border-neutral-200 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-2xl font-semibold text-neutral-400"
      >
        {user.profile_picture_url ? (
          <img src={user.profile_picture_url} alt="" className="h-full w-full object-cover" />
        ) : (
          user.username?.[0]?.toUpperCase()
        )}
      </div>
      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFile}
          className="hidden"
          id="avatar-upload"
        />
        <label
          htmlFor="avatar-upload"
          className="cursor-pointer inline-block rounded-lg border border-neutral-300 dark:border-neutral-600 px-4 py-2 text-sm font-medium hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
        >
          {uploading ? t("profile.saving") : t("profile.changePhoto")}
        </label>
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      </div>
    </div>
  );
}

function OverviewTab() {
  const { t } = useTranslation();
  const { user, accessToken, refreshUser, applyNewToken, logout } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email || "");
  const [preferences, setPreferences] = useState(user.preferences.join(", "));
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
      const payload = {
        preferences: preferences.split(",").map((p) => p.trim()).filter(Boolean),
      };
      if (username !== user.username) payload.username = username;
      if (email !== (user.email || "")) payload.email = email;

      const result = await updateMe(accessToken, payload);

      if (result.access_token) {
        // Username changed — the old token is dead the moment the
        // rename happened server-side, swap in the new one now.
        await applyNewToken(result.access_token);
      } else {
        await refreshUser();
      }
      setMessage(t("profile.profileUpdated"));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("profile.updateError"));
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUploaded = async () => {
    await refreshUser();
    setMessage(t("profile.profileUpdated"));
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
        <AvatarUploader user={user} accessToken={accessToken} onUploaded={handleAvatarUploaded} />
      </div>

      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
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
          <label htmlFor="profile-username" className="text-sm font-medium">{t("profile.username")}</label>
          <input
            id="profile-username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={3}
            maxLength={32}
            pattern="^[a-zA-Z0-9_.\-]+$"
            className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
          />
          <p className="mt-1 text-xs text-neutral-400">{t("profile.usernameHint")}</p>
        </div>

        {user.email !== undefined && (
          <div>
            <label htmlFor="profile-email" className="text-sm font-medium">{t("profile.email")}</label>
            <input
              id="profile-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
            />
            <p className="mt-1 text-xs text-neutral-400">{t("profile.emailHint")}</p>
          </div>
        )}

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
  const [searchParams, setSearchParams] = useSearchParams();

  const TABS = [
    { key: "Overview", label: t("profile.tabOverview") },
    { key: "Earnings", label: t("profile.tabEarnings") },
    { key: "Notifications", label: t("profile.tabNotifications") },
  ];

  const requestedTab = searchParams.get("tab");
  const activeTab = TABS.some((tab) => tab.key === requestedTab) ? requestedTab : "Overview";
  const setActiveTab = (key) => setSearchParams(key === "Overview" ? {} : { tab: key });

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

      <div className="mt-6 flex gap-1 border-b border-neutral-200 dark:border-neutral-700 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`shrink-0 px-4 py-2 text-sm font-medium transition ${
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
