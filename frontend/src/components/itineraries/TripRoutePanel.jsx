import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Navigation, Clock, Route, Phone, Mail, Globe, LocateFixed } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import RouteMap from "../map/RouteMap";
import { previewRoute, ApiError } from "../../api/client";

const CITY_PRESETS = [
  { label: "Douala", lat: 4.0511, lng: 9.7679 },
  { label: "Yaoundé", lat: 3.8480, lng: 11.5021 },
  { label: "Bafoussam", lat: 5.4737, lng: 10.4176 },
  { label: "Bamenda", lat: 5.9631, lng: 10.1591 },
  { label: "Limbe", lat: 4.0163, lng: 9.2136 },
];

/**
 * Shown both mid-planning (as a wizard step, before the trip is saved)
 * and on a saved trip's card ("View route") — same component either
 * way, it only needs an ordered list of destination ids.
 */
export default function TripRoutePanel({ destinationIds }) {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [start, setStart] = useState(null); // { lat, lng, label } | null
  const [locating, setLocating] = useState(false);
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const useMyLocation = () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setStart({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: t("itineraries.yourLocation", "Your location") });
        setLocating(false);
      },
      () => setLocating(false),
      { timeout: 8000 }
    );
  };

  useEffect(() => {
    if (destinationIds.length === 0) return;
    setLoading(true);
    setError(null);
    previewRoute(accessToken, {
      destination_ids: destinationIds,
      start_lat: start?.lat,
      start_lng: start?.lng,
      start_label: start?.label,
    })
      .then(setRoute)
      .catch((err) => setError(err instanceof ApiError ? err.detail : t("auth.genericError")))
      .finally(() => setLoading(false));
  }, [destinationIds, start, accessToken, t]);

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-medium text-neutral-500 mb-2">{t("itineraries.startingFrom", "Starting from")}</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={useMyLocation}
            disabled={locating}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
              start?.label === t("itineraries.yourLocation", "Your location")
                ? "bg-canopy-500 text-white"
                : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300"
            }`}
          >
            <LocateFixed size={13} />
            {locating ? t("itineraries.locating", "Locating…") : t("itineraries.myLocation", "My location")}
          </button>
          {CITY_PRESETS.map((c) => (
            <button
              key={c.label}
              type="button"
              onClick={() => setStart({ lat: c.lat, lng: c.lng, label: c.label })}
              className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                start?.label === c.label ? "bg-canopy-500 text-white" : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300"
              }`}
            >
              {c.label}
            </button>
          ))}
          {start && (
            <button type="button" onClick={() => setStart(null)} className="px-3 py-1.5 rounded-full text-xs text-neutral-400 underline">
              {t("itineraries.clearStart", "Clear")}
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {route && (
        <>
          <RouteMap stops={route.stops} geometry={route.geometry} height="300px" />

          <div className="flex gap-4">
            <div className="flex items-center gap-1.5 text-sm">
              <Route size={15} className="text-canopy-500" />
              <span className="font-data font-medium">{route.total_distance_km} km</span>
            </div>
            {route.total_duration_minutes != null && (
              <div className="flex items-center gap-1.5 text-sm">
                <Clock size={15} className="text-canopy-500" />
                <span className="font-data font-medium">
                  {Math.floor(route.total_duration_minutes / 60)}h{Math.round(route.total_duration_minutes % 60)}m
                </span>
              </div>
            )}
            {route.method === "straight_line" && (
              <span className="text-xs text-neutral-400 italic">{t("itineraries.straightLineNote", "Straight-line estimate, not a real road route")}</span>
            )}
          </div>

          {route.transport_suggestions.length > 0 && (
            <div>
              <p className="text-xs font-medium text-neutral-500 mb-2 inline-flex items-center gap-1">
                <Navigation size={13} />{t("itineraries.getThere", "How to get there")}
              </p>
              <div className="space-y-2">
                {route.transport_suggestions.map((c) => (
                  <motion.div
                    key={c.name}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="rounded-xl border border-neutral-200 dark:border-neutral-700 p-3"
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-sm">{c.name}</p>
                      <span className="text-[10px] uppercase tracking-wide text-neutral-400">{t(`itineraries.transportType.${c.type}`, c.type)}</span>
                    </div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">{c.best_for}</p>
                    <div className="flex flex-wrap gap-3 mt-2 text-xs">
                      {c.phone && (
                        <a href={`tel:${c.phone.replace(/\s/g, "")}`} className="inline-flex items-center gap-1 text-canopy-600 dark:text-canopy-400">
                          <Phone size={12} />{c.phone}
                        </a>
                      )}
                      {c.email && (
                        <a href={`mailto:${c.email}`} className="inline-flex items-center gap-1 text-canopy-600 dark:text-canopy-400">
                          <Mail size={12} />{c.email}
                        </a>
                      )}
                      {c.website && (
                        <a href={c.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-canopy-600 dark:text-canopy-400">
                          <Globe size={12} />{t("itineraries.website", "Website")}
                        </a>
                      )}
                    </div>
                    {c.note && <p className="text-xs text-neutral-400 mt-1.5">{c.note}</p>}
                  </motion.div>
                ))}
              </div>
              <p className="mt-2 text-[11px] text-neutral-400">
                {t("itineraries.transportDisclaimer", "Coverage shown is a general guide — confirm exact routes and current schedules directly with the operator.")}
              </p>
            </div>
          )}
        </>
      )}

      {loading && !route && <p className="text-sm text-neutral-400">{t("itineraries.loading")}</p>}
    </div>
  );
}
