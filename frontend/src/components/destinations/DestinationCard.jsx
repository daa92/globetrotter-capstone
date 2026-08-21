import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Star, ThumbsUp, ThumbsDown, Play } from "lucide-react";
import DestinationImage from "./DestinationImage";
import { useAuth } from "../../context/AuthContext";
import { likeDestination, dislikeDestination, ApiError } from "../../api/client";

function RatingBadge({ rating }) {
  if (rating == null) return null;
  return (
    <span className="inline-flex items-center gap-0.5 text-xs font-medium text-amber-500">
      <Star size={12} fill="currentColor" />
      {rating.toFixed(1)}
    </span>
  );
}

function VoteButtons({ destination }) {
  const { user, accessToken } = useAuth();
  const [likes, setLikes] = useState(destination.likes ?? 0);
  const [dislikes, setDislikes] = useState(destination.dislikes ?? 0);
  const [busy, setBusy] = useState(false);

  // Read-only display for logged-out visitors — voting needs an account,
  // same rule as feedback (see FeedbackWidget), so no point offering
  // buttons that will just 401.
  if (!user) {
    return (
      <span className="inline-flex items-center gap-3 text-xs text-neutral-400">
        <span className="inline-flex items-center gap-1"><ThumbsUp size={13} />{likes}</span>
        <span className="inline-flex items-center gap-1"><ThumbsDown size={13} />{dislikes}</span>
      </span>
    );
  }

  const vote = async (e, kind) => {
    e.stopPropagation(); // card itself is often clickable — don't trigger that too
    if (busy) return;
    setBusy(true);
    try {
      const result = await (kind === "like" ? likeDestination : dislikeDestination)(accessToken, destination.id);
      setLikes(result.likes);
      setDislikes(result.dislikes);
    } catch (err) {
      // Silent — voting is a minor interaction, not worth an error banner on a card.
      if (!(err instanceof ApiError)) throw err;
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="inline-flex items-center gap-3 text-xs">
      <button
        onClick={(e) => vote(e, "like")}
        disabled={busy}
        className="inline-flex items-center gap-1 text-neutral-500 hover:text-teal-600 dark:text-neutral-400 dark:hover:text-teal-400 disabled:opacity-50"
      >
        <ThumbsUp size={13} />{likes}
      </button>
      <button
        onClick={(e) => vote(e, "dislike")}
        disabled={busy}
        className="inline-flex items-center gap-1 text-neutral-500 hover:text-red-500 dark:text-neutral-400 dark:hover:text-red-400 disabled:opacity-50"
      >
        <ThumbsDown size={13} />{dislikes}
      </button>
    </span>
  );
}

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
      <div className="relative">
        <DestinationImage destination={destination} className="h-44 w-full object-cover" />
        {destination.video_url && (
          <span className="absolute bottom-2 right-2 inline-flex items-center gap-1 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white">
            <Play size={11} fill="currentColor" />
            {t("explore.hasVideo", "Video")}
          </span>
        )}
      </div>
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
          <p className="text-xs text-neutral-500 dark:text-neutral-400 inline-flex items-center gap-2">
            {destination.region}
            <RatingBadge rating={destination.rating} />
          </p>
        )}

        {destination.description && (
          <p className="mt-2 line-clamp-2 text-sm text-neutral-600 dark:text-neutral-300">{destination.description}</p>
        )}
        {isLive && destination.address && (
          <p className="mt-2 line-clamp-1 text-sm text-neutral-600 dark:text-neutral-300">{destination.address}</p>
        )}

        {destination.how_to_get_there && (
          <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
            {t("explore.fromCity", "From")} {destination.how_to_get_there.from}: ~{destination.how_to_get_there.distance_km} km
            {destination.how_to_get_there.duration_minutes != null && ` (~${Math.round(destination.how_to_get_there.duration_minutes / 60)}h${destination.how_to_get_there.duration_minutes % 60}m)`}
          </p>
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

        {!isLive && destination.id && (
          <div className="mt-3 flex items-center justify-between">
            <VoteButtons destination={destination} />
          </div>
        )}

        {action && <div className="mt-3">{action}</div>}
      </div>
    </motion.div>
  );
}
