import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import DestinationImage from "./DestinationImage";

/**
 * Renders either a curated destination (name, region, description, tags,
 * avg_cost_fcfa) or a live POI result from /geo/poi (name, category,
 * address, phone, opening_hours — no description/tags/cost). Each
 * optional field is only rendered if present, so the same card works for
 * both without a separate component.
 */
export default function DestinationCard({ destination, action, onClick, index = 0 }) {
  const { t } = useTranslation();
  const isLive = destination.category != null && destination.tags == null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.04, 0.4) }}
      whileHover={{ y: -4 }}
      onClick={onClick}
      className={`overflow-hidden rounded-2xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 transition hover:shadow-xl ${onClick ? "cursor-pointer" : ""}`}
    >
      <DestinationImage destination={destination} className="h-44 w-full object-cover" />
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold">{destination.name}</h3>
          {destination.avg_cost_fcfa != null && (
            <span className="whitespace-nowrap text-xs text-neutral-500 dark:text-neutral-400">
              ~{destination.avg_cost_fcfa.toLocaleString()} FCFA
            </span>
          )}
        </div>

        {isLive ? (
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            {t(`poiCategories.${destination.category}`, destination.category)}
            {destination._distanceKm != null && ` · ${destination._distanceKm.toFixed(1)} km`}
          </p>
        ) : (
          <p className="text-xs text-neutral-500 dark:text-neutral-400">{destination.region}</p>
        )}

        {destination.description && (
          <p className="mt-2 line-clamp-2 text-sm text-neutral-600 dark:text-neutral-300">{destination.description}</p>
        )}
        {isLive && destination.address && (
          <p className="mt-2 line-clamp-1 text-sm text-neutral-600 dark:text-neutral-300">{destination.address}</p>
        )}

        {destination.tags && (
          <div className="mt-3 flex flex-wrap gap-1">
            {destination.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-teal-50 dark:bg-teal-950/50 px-2 py-0.5 text-xs text-teal-700 dark:text-teal-300"
              >
                {t(`tags.${tag}`, tag)}
              </span>
            ))}
          </div>
        )}
        {action && <div className="mt-3">{action}</div>}
      </div>
    </motion.div>
  );
}
