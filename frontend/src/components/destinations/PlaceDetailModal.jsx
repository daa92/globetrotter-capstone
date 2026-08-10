import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { AnimatePresence, motion } from "framer-motion";
import { X, MapPin, Phone, Clock, ExternalLink } from "lucide-react";
import DestinationImage from "./DestinationImage";
import { getPlaceSummary } from "../../api/client";

/**
 * Shows details for either:
 *   - a curated destination (has its own description/image already — no
 *     extra fetch needed), or
 *   - a live/OSM place (restaurant, airport, etc. from /geo/poi, or a
 *     Nominatim search result) — these have a name and coordinates but no
 *     rich description, so we look one up via Wikipedia on open. Most
 *     small local places won't have a Wikipedia article, and that's a
 *     completely normal outcome, not an error — shown plainly rather than
 *     as a failure state.
 */
export default function PlaceDetailModal({ place, onClose }) {
  const { t, i18n } = useTranslation();
  const [summary, setSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  const isCurated = place?.description != null;

  useEffect(() => {
    if (!place || isCurated) return;
    let cancelled = false;
    setLoadingSummary(true);
    setSummary(null);
    getPlaceSummary(place.name, i18n.language.startsWith("fr") ? "fr" : "en")
      .then((result) => {
        if (!cancelled) setSummary(result);
      })
      .catch(() => {
        if (!cancelled) setSummary({ found: false });
      })
      .finally(() => {
        if (!cancelled) setLoadingSummary(false);
      });
    return () => {
      cancelled = true;
    };
  }, [place, isCurated, i18n.language]);

  return (
    <AnimatePresence>
      {place && (
        <motion.div
          className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50 p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white dark:bg-neutral-800 shadow-2xl"
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.18 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative">
              {isCurated ? (
                <DestinationImage destination={place} className="h-56 w-full object-cover" />
              ) : summary?.image_url ? (
                <img src={summary.image_url} alt={place.name} className="h-56 w-full object-cover" />
              ) : (
                <div
                  className="flex h-40 w-full items-center justify-center"
                  style={{ background: "linear-gradient(135deg, #0F2027, #23393F)" }}
                >
                  <MapPin className="h-10 w-10 text-white/60" />
                </div>
              )}
              <button
                onClick={onClose}
                className="absolute right-3 top-3 rounded-full bg-black/50 p-1.5 text-white hover:bg-black/70"
                aria-label={t("explore.close")}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-5">
              <h2 className="text-xl font-bold">{place.name}</h2>
              {(place.region || place.category) && (
                <p className="text-sm text-neutral-500 dark:text-neutral-400">
                  {place.region || t(`poiCategories.${place.category}`, place.category)}
                </p>
              )}

              {isCurated ? (
                <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-300">{place.description}</p>
              ) : loadingSummary ? (
                <p className="mt-3 text-sm text-neutral-400">{t("explore.loadingDescription")}</p>
              ) : summary?.found ? (
                <>
                  <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-300">{summary.extract}</p>
                  {summary.wikipedia_url && (
                    <a
                      href={summary.wikipedia_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex items-center gap-1 text-xs text-teal-700 dark:text-teal-400 hover:underline"
                    >
                      {t("explore.viewOnWikipedia")} <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </>
              ) : (
                <p className="mt-3 text-sm text-neutral-400">{t("explore.noDescription")}</p>
              )}

              {(place.address || place.phone || place.opening_hours) && (
                <div className="mt-4 space-y-1.5 border-t border-neutral-100 dark:border-neutral-700 pt-4 text-sm">
                  {place.address && (
                    <p className="flex items-center gap-2 text-neutral-600 dark:text-neutral-300">
                      <MapPin className="h-4 w-4 shrink-0 text-neutral-400" /> {place.address}
                    </p>
                  )}
                  {place.phone && (
                    <p className="flex items-center gap-2 text-neutral-600 dark:text-neutral-300">
                      <Phone className="h-4 w-4 shrink-0 text-neutral-400" /> {place.phone}
                    </p>
                  )}
                  {place.opening_hours && (
                    <p className="flex items-center gap-2 text-neutral-600 dark:text-neutral-300">
                      <Clock className="h-4 w-4 shrink-0 text-neutral-400" /> {place.opening_hours}
                    </p>
                  )}
                </div>
              )}

              {place.avg_cost_fcfa != null && (
                <p className="mt-3 text-sm font-medium" style={{ color: "#127C71" }}>
                  ~{place.avg_cost_fcfa.toLocaleString()} FCFA
                </p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
