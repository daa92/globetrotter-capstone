import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { listMyPlaces, deletePlace, ApiError } from "../api/client";
import PlaceForm from "../components/places/PlaceForm";

const STATUS_STYLES = {
  approved: "bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300",
  pending: "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300",
  rejected: "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300",
};

export default function MyPlaces() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [places, setPlaces] = useState(null);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null); // null | "new" | place object
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setPlaces(await listMyPlaces(accessToken));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
    }
  }, [accessToken, t]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id) => {
    setBusyId(id);
    try {
      await deletePlace(accessToken, id);
      setPlaces((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
    } finally {
      setBusyId(null);
    }
  };

  const handleDone = () => {
    setEditing(null);
    load();
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">{t("places.myPlaces", "My places")}</h1>
        {editing === null && (
          <button
            onClick={() => setEditing("new")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 text-sm font-medium"
          >
            <Plus size={15} />
            {t("places.addPlace", "Add a place")}
          </button>
        )}
      </div>

      {editing !== null && (
        <div className="mb-8 rounded-2xl border border-neutral-200 dark:border-neutral-700 p-4">
          <PlaceForm place={editing === "new" ? null : editing} onDone={handleDone} onCancel={() => setEditing(null)} />
        </div>
      )}

      {error && <p className="text-sm text-red-500 mb-4">{error}</p>}

      {places === null ? (
        <p className="text-sm text-neutral-400">{t("places.loading", "Loading…")}</p>
      ) : places.length === 0 ? (
        <p className="text-sm text-neutral-400">{t("places.noneYet", "You haven't added any places yet.")}</p>
      ) : (
        <div className="space-y-3">
          {places.map((p) => (
            <div key={p.id} className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium">{p.name}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[p.status]}`}>
                      {t(`places.status.${p.status}`, p.status)}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">{p.region}</p>
                  <p className="text-sm text-neutral-600 dark:text-neutral-300 mt-1 line-clamp-2">{p.description}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button
                    onClick={() => setEditing(p)}
                    className="p-1.5 rounded-lg text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                    aria-label={t("places.edit", "Edit")}
                  >
                    <Pencil size={15} />
                  </button>
                  <button
                    onClick={() => handleDelete(p.id)}
                    disabled={busyId === p.id}
                    className="p-1.5 rounded-lg text-neutral-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40 disabled:opacity-50"
                    aria-label={t("places.delete", "Delete")}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
