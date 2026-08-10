import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import * as api from "../../api/client";
import { ApiError } from "../../api/client";

const CATEGORY_COLORS = {
  referral: "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300",
  payout: "bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300",
  place: "bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300",
  security: "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300",
  admin: "bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300",
  system: "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300",
};

export default function NotificationCenter({ accessToken }) {
  const { t } = useTranslation();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(new Set());

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setNotifications(await api.listNotifications(accessToken));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (accessToken) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleMarkAllRead = async () => {
    await api.markNotificationsRead(accessToken, { all: true });
    await load();
  };

  const handleMarkSelectedRead = async () => {
    await api.markNotificationsRead(accessToken, { ids: [...selected] });
    setSelected(new Set());
    await load();
  };

  const handleDeleteSelected = async () => {
    await api.deleteNotifications(accessToken, { ids: [...selected] });
    setSelected(new Set());
    await load();
  };

  const handleDeleteAll = async () => {
    await api.deleteNotifications(accessToken, { all: true });
    await load();
  };

  const handleDeleteOne = async (id) => {
    await api.deleteNotification(accessToken, id);
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  if (loading) return <p className="text-neutral-400">{t("notifications.loading")}</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {t("notifications.unreadOf", { unread: notifications.filter((n) => !n.is_read).length, total: notifications.length })}
        </p>
        <div className="flex gap-2 text-sm">
          {selected.size > 0 && (
            <>
              <button onClick={handleMarkSelectedRead} className="text-teal-700 dark:text-teal-400 hover:underline">
                {t("notifications.markSelectedRead", { count: selected.size })}
              </button>
              <button onClick={handleDeleteSelected} className="text-red-600 hover:underline">
                {t("notifications.deleteSelected", { count: selected.size })}
              </button>
            </>
          )}
          <button onClick={handleMarkAllRead} className="text-teal-700 dark:text-teal-400 hover:underline">
            {t("notifications.markAllRead")}
          </button>
          <button onClick={handleDeleteAll} className="text-red-600 hover:underline">
            {t("notifications.deleteAll")}
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {notifications.length === 0 ? (
          <p className="text-neutral-400">{t("notifications.noNotifications")}</p>
        ) : (
          notifications.map((n) => (
            <div
              key={n.id}
              className={`flex items-start gap-3 rounded-xl border p-3 transition ${
                n.is_read
                  ? "border-neutral-200 dark:border-neutral-700"
                  : "border-teal-300 dark:border-teal-700 bg-teal-50/40 dark:bg-teal-950/20"
              }`}
            >
              <input type="checkbox" checked={selected.has(n.id)} onChange={() => toggleSelect(n.id)} className="mt-1" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CATEGORY_COLORS[n.category] || CATEGORY_COLORS.system}`}>
                    {t(`notifications.categories.${n.category}`, n.category)}
                  </span>
                  <p className="font-medium">{n.title}</p>
                </div>
                <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">{n.message}</p>
                <p className="mt-1 text-xs text-neutral-400">{new Date(n.created_at).toLocaleString()}</p>
              </div>
              <button onClick={() => handleDeleteOne(n.id)} className="text-xs text-red-500 hover:underline">
                {t("notifications.delete")}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
