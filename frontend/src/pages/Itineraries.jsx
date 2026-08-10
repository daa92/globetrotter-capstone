import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { createItinerary, deleteItinerary, listItineraries, searchDestinations, ApiError } from "../api/client";

export default function Itineraries() {
  const { t } = useTranslation();
  const { isAuthenticated, accessToken, loading: authLoading } = useAuth();
  const [itineraries, setItineraries] = useState([]);
  const [destinations, setDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [title, setTitle] = useState("");
  const [selectedDestinations, setSelectedDestinations] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [mine, catalogue] = await Promise.all([listItineraries(accessToken), searchDestinations({})]);
      setItineraries(mine);
      setDestinations(catalogue);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("itineraries.loadError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && isAuthenticated) load();
    else if (!authLoading) setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated]);

  const toggleDestination = (id) => {
    setSelectedDestinations((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      await createItinerary(accessToken, {
        title,
        destinations: selectedDestinations,
        start_date: startDate,
        end_date: endDate,
      });
      setTitle("");
      setSelectedDestinations([]);
      setStartDate("");
      setEndDate("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("itineraries.createError"));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteItinerary(accessToken, id);
      setItineraries((prev) => prev.filter((it) => it.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("itineraries.deleteError"));
    }
  };

  if (!authLoading && !isAuthenticated) {
    return (
      <section className="mx-auto max-w-md px-6 py-24 text-center">
        <h1 className="text-2xl font-bold">{t("itineraries.planTitle")}</h1>
        <p className="mt-2 text-neutral-500 dark:text-neutral-400">{t("itineraries.planBody")}</p>
        <Link
          to="/login"
          className="mt-6 inline-block rounded-full px-6 py-2 font-semibold text-white transition"
          style={{ backgroundColor: "#127C71" }}
        >
          {t("itineraries.login")}
        </Link>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold">{t("itineraries.title")}</h1>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleCreate} className="mt-6 space-y-4 rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
        <h2 className="font-semibold">{t("itineraries.newTripTitle")}</h2>
        <input
          type="text"
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t("itineraries.tripTitlePlaceholder")}
          className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
        />

        <div>
          <p className="mb-2 text-sm font-medium">{t("itineraries.destinations")}</p>
          <div className="flex flex-wrap gap-2">
            {destinations.map((d) => (
              <button
                type="button"
                key={d.id}
                onClick={() => toggleDestination(d.id)}
                className={`rounded-full border px-3 py-1 text-sm transition ${
                  selectedDestinations.includes(d.id)
                    ? "text-white border-transparent"
                    : "border-neutral-300 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300"
                }`}
                style={selectedDestinations.includes(d.id) ? { backgroundColor: "#127C71" } : {}}
              >
                {d.name}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="itinerary-start-date" className="text-sm font-medium">{t("itineraries.startDate")}</label>
            <input
              id="itinerary-start-date"
              type="date"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
            />
          </div>
          <div className="flex-1">
            <label htmlFor="itinerary-end-date" className="text-sm font-medium">{t("itineraries.endDate")}</label>
            <input
              id="itinerary-end-date"
              type="date"
              required
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={creating || selectedDestinations.length === 0}
          className="w-full rounded-lg py-2 font-semibold text-white transition disabled:opacity-50"
          style={{ backgroundColor: "#127C71" }}
        >
          {creating ? t("itineraries.creating") : t("itineraries.createBtn")}
        </button>
      </form>

      <div className="mt-8 space-y-4">
        {loading ? (
          <p className="text-neutral-400">{t("itineraries.loading")}</p>
        ) : itineraries.length === 0 ? (
          <p className="text-neutral-400">{t("itineraries.noTrips")}</p>
        ) : (
          itineraries.map((it) => (
            <div
              key={it.id}
              className="flex items-center justify-between rounded-2xl border border-neutral-200 dark:border-neutral-700 p-4"
            >
              <div>
                <p className="font-semibold">{it.title}</p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">
                  {it.start_date} → {it.end_date} · {t("itineraries.destinationsCount", { count: it.destinations.length })}
                </p>
              </div>
              <button onClick={() => handleDelete(it.id)} className="text-sm text-red-600 hover:underline">
                {t("itineraries.delete")}
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
