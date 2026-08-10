import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { getRecommendations, ApiError } from "../api/client";
import DestinationCard from "../components/destinations/DestinationCard";

export default function Recommendations() {
  const { t } = useTranslation();
  const { isAuthenticated, accessToken, loading: authLoading } = useAuth();
  const [destinations, setDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) {
      setLoading(false);
      return;
    }
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const results = await getRecommendations(accessToken, 12);
        setDestinations(results);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
      } finally {
        setLoading(false);
      }
    })();
  }, [authLoading, isAuthenticated, accessToken, t]);

  if (!authLoading && !isAuthenticated) {
    return (
      <section className="mx-auto max-w-md px-6 py-24 text-center">
        <h1 className="text-2xl font-bold">{t("recommendations.personalTitle")}</h1>
        <p className="mt-2 text-neutral-500 dark:text-neutral-400">{t("recommendations.personalBody")}</p>
        <Link
          to="/login"
          className="mt-6 inline-block rounded-full px-6 py-2 font-semibold text-white transition"
          style={{ backgroundColor: "#127C71" }}
        >
          {t("recommendations.login")}
        </Link>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold">{t("recommendations.title")}</h1>
      <p className="mt-1 text-neutral-500 dark:text-neutral-400">{t("recommendations.subtitle")}</p>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <p className="text-neutral-400">{t("recommendations.loading")}</p>
        ) : destinations.length === 0 ? (
          <p className="text-neutral-400">{t("recommendations.noResults")}</p>
        ) : (
          destinations.map((d) => <DestinationCard key={d.id} destination={d} />)
        )}
      </div>
    </section>
  );
}
