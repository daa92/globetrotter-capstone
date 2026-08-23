import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import { searchDestinations, getPoiCategories, searchPois, ApiError } from "../api/client";
import DestinationsMap from "../components/map/DestinationsMap";
import DestinationCard from "../components/destinations/DestinationCard";
import PlaceDetailModal from "../components/destinations/PlaceDetailModal";
import SearchAutocomplete from "../components/search/SearchAutocomplete";
import FilterPanel from "../components/search/FilterPanel";
import { haversineDistanceKm } from "../utils/geo";

const PAGE_SIZE = 10;

export default function Explore() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [allDestinations, setAllDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [query, setQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState([]);
  const [maxBudget, setMaxBudget] = useState(15000);
  const [budgetUnlimited, setBudgetUnlimited] = useState(true);

  const [distanceEnabled, setDistanceEnabled] = useState(false);
  const [maxDistanceKm, setMaxDistanceKm] = useState(200);
  const [userLocation, setUserLocation] = useState(null);
  const [geoStatus, setGeoStatus] = useState("idle"); // idle | pending | ok | denied

  const [poiCategories, setPoiCategories] = useState([]);
  const [selectedPoiCategories, setSelectedPoiCategories] = useState([]);
  const [livePlaces, setLivePlaces] = useState([]);
  const [loadingLive, setLoadingLive] = useState(false);
  const [liveError, setLiveError] = useState(null);

  const [selectedPlace, setSelectedPlace] = useState(null);
  const [page, setPage] = useState(1);

  // Fetch the curated catalogue once — filtering instantly client-side
  // beats round-tripping to the backend on every keystroke/slider tick.
  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        setAllDestinations(await searchDestinations({}));
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
      } finally {
        setLoading(false);
      }
    })();
    getPoiCategories()
      .then((res) => setPoiCategories(res.categories))
      .catch(() => setPoiCategories([])); // live-search categories are an enhancement, not core — fail quietly
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleToggleDistance = () => {
    const next = !distanceEnabled;
    setDistanceEnabled(next);
    if (next && !userLocation) {
      setGeoStatus("pending");
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
          setGeoStatus("ok");
        },
        () => setGeoStatus("denied"),
        { timeout: 10000 }
      );
    }
  };

  const toggleTag = (tag) => {
    setPage(1);
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((x) => x !== tag) : [...prev, tag]));
  };

  const togglePoiCategory = (cat) => {
    setSelectedPoiCategories((prev) => (prev.includes(cat) ? prev.filter((x) => x !== cat) : [...prev, cat]));
  };

  // Live POI search — only makes sense once we have a center point
  // (the user's location) and at least one category picked.
  useEffect(() => {
    if (!distanceEnabled || geoStatus !== "ok" || selectedPoiCategories.length === 0) {
      setLivePlaces([]);
      return;
    }
    let cancelled = false;
    setLoadingLive(true);
    setLiveError(null);
    Promise.all(
      selectedPoiCategories.map((cat) =>
        searchPois(cat, userLocation.lat, userLocation.lon, maxDistanceKm * 1000).then((res) => res.results)
      )
    )
      .then((resultsPerCategory) => {
        if (cancelled) return;
        const merged = resultsPerCategory.flat().map((p) => ({
          ...p,
          id: `poi-${p.category}-${p.latitude}-${p.longitude}`,
          _distanceKm: haversineDistanceKm(userLocation.lat, userLocation.lon, p.latitude, p.longitude),
        }));
        merged.sort((a, b) => a._distanceKm - b._distanceKm);
        setLivePlaces(merged);
      })
      .catch((err) => {
        if (!cancelled) setLiveError(err instanceof ApiError ? err.detail : t("explore.liveSearchError"));
      })
      .finally(() => {
        if (!cancelled) setLoadingLive(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [distanceEnabled, geoStatus, selectedPoiCategories, userLocation, maxDistanceKm]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    let results = allDestinations.filter((d) => {
      const matchesQuery =
        !q ||
        d.name.toLowerCase().includes(q) ||
        d.description.toLowerCase().includes(q) ||
        d.tags.some((tag) => tag.toLowerCase().includes(q) || t(`tags.${tag}`, tag).toLowerCase().includes(q));
      const matchesTags = selectedTags.length === 0 || selectedTags.some((tag) => d.tags.includes(tag));
      const matchesBudget = budgetUnlimited || d.avg_cost_fcfa == null || d.avg_cost_fcfa <= maxBudget;
      return matchesQuery && matchesTags && matchesBudget;
    });

    if (distanceEnabled && userLocation) {
      results = results
        .map((d) => ({ ...d, _distanceKm: haversineDistanceKm(userLocation.lat, userLocation.lon, d.latitude, d.longitude) }))
        .filter((d) => d._distanceKm <= maxDistanceKm)
        .sort((a, b) => a._distanceKm - b._distanceKm);
    }

    return results;
  }, [allDestinations, query, selectedTags, maxBudget, budgetUnlimited, distanceEnabled, userLocation, maxDistanceKm, t]);

  const totalResults = filtered.length + livePlaces.length;
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pagedResults = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const mapResults = [...filtered, ...livePlaces];

  return (
    <section className="mx-auto max-w-6xl px-6 py-12">
      <motion.h1 initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="text-3xl font-bold">
        {t("explore.title")}
      </motion.h1>
      <p className="mt-1 text-neutral-500 dark:text-neutral-400">
        {t("explore.subtitle", { count: allDestinations.length })}
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <SearchAutocomplete
          destinations={allDestinations}
          value={query}
          onChange={(v) => {
            setQuery(v);
            setPage(1);
          }}
          onSelectDestination={(d) => setQuery(d.name)}
          placeholder={t("explore.searchPlaceholder")}
        />
      </div>

      <FilterPanel
        selectedTags={selectedTags}
        onToggleTag={toggleTag}
        maxBudget={maxBudget}
        onMaxBudgetChange={(v) => {
          setMaxBudget(v);
          setPage(1);
        }}
        budgetUnlimited={budgetUnlimited}
        onToggleBudgetUnlimited={() => setBudgetUnlimited((v) => !v)}
        distanceEnabled={distanceEnabled}
        onToggleDistance={handleToggleDistance}
        maxDistanceKm={maxDistanceKm}
        onMaxDistanceChange={setMaxDistanceKm}
        geoStatus={geoStatus}
        poiCategories={poiCategories}
        selectedPoiCategories={selectedPoiCategories}
        onTogglePoiCategory={togglePoiCategory}
      />

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="mt-6">
          <DestinationsMap destinations={mapResults} onSelect={setSelectedPlace} />
        </div>
      )}

      <div className="mt-6 flex items-center justify-between">
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {t("explore.showingCount", { shown: pagedResults.length, total: totalResults })}
        </p>
      </div>

      <motion.div layout className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <p className="text-neutral-400">{t("explore.loading")}</p>
        ) : pagedResults.length === 0 ? (
          <p className="text-neutral-400">{t("explore.noResults")}</p>
        ) : (
          <AnimatePresence mode="popLayout">
            {pagedResults.map((d, i) => (
              <DestinationCard key={d.id} destination={d} index={i} onClick={() => navigate(`/destinations/${d.id}`)} />
            ))}
          </AnimatePresence>
        )}
      </motion.div>

      {totalPages > 1 && (
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`h-9 min-w-[36px] rounded-lg border px-3 text-sm font-medium transition ${
                p === page
                  ? "text-white border-transparent"
                  : "border-neutral-300 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
              }`}
              style={p === page ? { backgroundColor: "#127C71" } : {}}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {selectedPoiCategories.length > 0 && distanceEnabled && geoStatus === "ok" && (
        <div className="mt-12">
          <h2 className="text-xl font-bold">{t("explore.livePlaces")}</h2>
          {liveError && <p className="mt-2 text-sm text-red-600">{liveError}</p>}
          {loadingLive ? (
            <p className="mt-4 text-neutral-400">{t("explore.loadingLive")}</p>
          ) : (
            <motion.div layout className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <AnimatePresence mode="popLayout">
                {livePlaces.map((p, i) => (
                  <DestinationCard key={p.id} destination={p} index={i} onClick={() => setSelectedPlace(p)} />
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </div>
      )}

      <PlaceDetailModal place={selectedPlace} onClose={() => setSelectedPlace(null)} />
    </section>
  );
}
