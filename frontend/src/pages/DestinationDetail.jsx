import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronLeft, ChevronRight, Star, ThumbsUp, ThumbsDown, MapPin,
  Navigation, Trash2, Send, ArrowLeft, ExternalLink,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import AnimatedCanopyBackground from "../components/layout/AnimatedCanopyBackground";
import DestinationImage from "../components/destinations/DestinationImage";
import {
  getDestination, likeDestination, dislikeDestination, getMyDestinationVote,
  listComments, addComment, deleteComment, ApiError,
} from "../api/client";

// --- Gallery -----------------------------------------------------------

function Gallery({ destination }) {
  const media = [
    ...(destination.images?.length ? destination.images : destination.image_url ? [destination.image_url] : []),
    ...(destination.video_url ? [{ video: destination.video_url }] : []),
  ];
  const [index, setIndex] = useState(0);

  if (media.length === 0) {
    return <DestinationImage destination={destination} className="h-[45vh] sm:h-[55vh] w-full object-cover" />;
  }

  const current = media[index];
  const isVideo = typeof current === "object" && current.video;
  const go = (delta) => setIndex((i) => (i + delta + media.length) % media.length);

  return (
    <div className="relative h-[45vh] sm:h-[55vh] w-full overflow-hidden bg-black">
      <AnimatePresence mode="wait">
        <motion.div
          key={index}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="absolute inset-0"
        >
          {isVideo ? (
            <video src={current.video} controls className="h-full w-full object-contain bg-black" />
          ) : (
            <img src={current} alt={`${destination.name} ${index + 1}`} className="h-full w-full object-cover" />
          )}
        </motion.div>
      </AnimatePresence>

      {media.length > 1 && (
        <>
          <button
            onClick={() => go(-1)}
            aria-label="Previous"
            className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-black/50 hover:bg-black/70 text-white p-2"
          >
            <ChevronLeft size={20} />
          </button>
          <button
            onClick={() => go(1)}
            aria-label="Next"
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-black/50 hover:bg-black/70 text-white p-2"
          >
            <ChevronRight size={20} />
          </button>
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
            {media.map((_, i) => (
              <button
                key={i}
                onClick={() => setIndex(i)}
                aria-label={`Go to slide ${i + 1}`}
                className={`h-1.5 rounded-full transition-all ${i === index ? "w-6 bg-white" : "w-1.5 bg-white/50"}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// --- Comments ------------------------------------------------------------

function Comments({ destinationId }) {
  const { t } = useTranslation();
  const { user, accessToken } = useAuth();
  const [comments, setComments] = useState(null);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    listComments(destinationId).then(setComments).catch(() => setComments([]));
  }, [destinationId]);

  useEffect(() => {
    load();
  }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    setSending(true);
    setError(null);
    try {
      await addComment(accessToken, destinationId, message.trim());
      setMessage("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
    } finally {
      setSending(false);
    }
  };

  const remove = async (commentId) => {
    try {
      await deleteComment(accessToken, destinationId, commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch {
      // keep it simple — comment stays visible if delete failed
    }
  };

  return (
    <div className="mt-10">
      <h2 className="font-display text-xl font-semibold mb-4">{t("places.comments", "Comments")}</h2>

      {user ? (
        <form onSubmit={submit} className="flex gap-2 mb-6">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            maxLength={1000}
            placeholder={t("places.addComment", "Share your thoughts…")}
            className="flex-1 rounded-full border border-neutral-300 dark:border-neutral-700 bg-transparent px-4 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={sending || !message.trim()}
            className="rounded-full bg-canopy-500 hover:bg-canopy-700 disabled:opacity-50 text-white p-2.5"
            aria-label={t("places.send", "Send")}
          >
            <Send size={16} />
          </button>
        </form>
      ) : (
        <p className="text-sm text-neutral-400 mb-6">
          <Link to="/login" className="text-canopy-500 hover:underline">{t("feedback.loginLink", "Log in")}</Link>{" "}
          {t("places.toComment", "to leave a comment.")}
        </p>
      )}
      {error && <p className="text-sm text-red-500 mb-4">{error}</p>}

      {comments === null ? (
        <p className="text-sm text-neutral-400">{t("places.loading", "Loading…")}</p>
      ) : comments.length === 0 ? (
        <p className="text-sm text-neutral-400">{t("places.noComments", "No comments yet — be the first.")}</p>
      ) : (
        <div className="space-y-4">
          {comments.map((c) => (
            <div key={c.id} className="flex items-start justify-between gap-3 border-b border-neutral-100 dark:border-neutral-800 pb-4">
              <div>
                <p className="text-sm font-medium">{c.username}</p>
                <p className="text-sm text-neutral-600 dark:text-neutral-300 mt-0.5">{c.message}</p>
                <p className="text-xs text-neutral-400 mt-1">{new Date(c.created_at).toLocaleDateString()}</p>
              </div>
              {(user?.username === c.username || user?.is_admin) && (
                <button onClick={() => remove(c.id)} className="text-neutral-400 hover:text-red-500 shrink-0" aria-label={t("places.delete", "Delete")}>
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Page -----------------------------------------------------------------

export default function DestinationDetail() {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, accessToken } = useAuth();

  const [destination, setDestination] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [likes, setLikes] = useState(0);
  const [dislikes, setDislikes] = useState(0);
  const [myVote, setMyVote] = useState(null);

  useEffect(() => {
    getDestination(id)
      .then((d) => {
        setDestination(d);
        setLikes(d.likes ?? 0);
        setDislikes(d.dislikes ?? 0);
      })
      .catch(() => setNotFound(true));
    if (accessToken) {
      getMyDestinationVote(accessToken, id).then((v) => setMyVote(v.your_vote)).catch(() => {});
    }
  }, [id, accessToken]);

  const vote = async (kind) => {
    if (!accessToken) return navigate("/login");
    const result = await (kind === "like" ? likeDestination : dislikeDestination)(accessToken, id);
    setLikes(result.likes);
    setDislikes(result.dislikes);
    setMyVote(result.your_vote);
  };

  if (notFound) {
    return (
      <div className="max-w-lg mx-auto mt-24 text-center">
        <p className="text-neutral-400">{t("places.notFound", "Place not found.")}</p>
        <Link to="/explore" className="mt-3 inline-block text-canopy-500 hover:underline">{t("explore.close", "Back to explore")}</Link>
      </div>
    );
  }

  if (!destination) {
    return <div className="max-w-2xl mx-auto mt-24 text-center text-neutral-400">{t("places.loading", "Loading…")}</div>;
  }

  return (
    <div>
      <div className="relative">
        <Gallery destination={destination} />
        <button
          onClick={() => navigate(-1)}
          className="absolute top-4 left-4 inline-flex items-center gap-1.5 rounded-full bg-black/50 hover:bg-black/70 text-white text-sm px-3 py-1.5"
        >
          <ArrowLeft size={15} />
          {t("explore.close", "Back")}
        </button>
      </div>

      <div className="relative mx-auto max-w-5xl px-4 sm:px-6 -mt-10 sm:-mt-14">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main column */}
          <div className="lg:col-span-2 rounded-2xl bg-white dark:bg-neutral-900 shadow-xl p-5 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="font-display text-2xl sm:text-3xl font-semibold">{destination.name}</h1>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 inline-flex items-center gap-1 mt-1">
                  <MapPin size={13} />{destination.region}
                </p>
              </div>
              {destination.rating != null && (
                <span className="inline-flex items-center gap-1 rounded-full bg-goldhour-400/15 text-goldhour-500 px-3 py-1 text-sm font-medium">
                  <Star size={15} fill="currentColor" />{destination.rating.toFixed(1)}
                </span>
              )}
            </div>

            {destination.tags?.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5">
                {destination.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-canopy-500/10 text-canopy-700 dark:text-canopy-300 px-2.5 py-0.5 text-xs font-medium">
                    {t(`tags.${tag}`, tag)}
                  </span>
                ))}
              </div>
            )}

            <p className="mt-5 text-neutral-700 dark:text-neutral-200 leading-relaxed whitespace-pre-line">
              {destination.description}
            </p>

            {destination.wiki_url && (
              <a href={destination.wiki_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs text-canopy-500 hover:underline">
                {t("explore.viewOnWikipedia", "View on Wikipedia")} <ExternalLink size={11} />
              </a>
            )}

            {destination.price_list?.length > 0 && (
              <div className="mt-6">
                <h2 className="font-display text-lg font-semibold mb-2">{t("places.priceList", "Prices")}</h2>
                <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 divide-y divide-neutral-100 dark:divide-neutral-800">
                  {destination.price_list.map((p, i) => (
                    <div key={i} className="flex items-center justify-between px-4 py-2 text-sm">
                      <span>{p.item}</span>
                      <span className="font-data text-neutral-500">{p.price_fcfa.toLocaleString()} FCFA</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Comments destinationId={id} />
          </div>

          {/* Sticky sidebar */}
          <div className="lg:col-span-1">
            <div className="rounded-2xl bg-white dark:bg-neutral-900 shadow-xl p-5 space-y-5 lg:sticky lg:top-24">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => vote("like")}
                  className={`flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl py-2 text-sm font-medium ${
                    myVote === "like" ? "bg-canopy-500 text-white" : "bg-neutral-100 dark:bg-neutral-800"
                  }`}
                >
                  <ThumbsUp size={15} />{likes}
                </button>
                <button
                  onClick={() => vote("dislike")}
                  className={`flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl py-2 text-sm font-medium ${
                    myVote === "dislike" ? "bg-laterite-600 text-white" : "bg-neutral-100 dark:bg-neutral-800"
                  }`}
                >
                  <ThumbsDown size={15} />{dislikes}
                </button>
              </div>

              {destination.avg_cost_fcfa != null && (
                <div>
                  <p className="text-xs text-neutral-400">{t("places.avgCost", "Avg cost")}</p>
                  <p className="font-data text-lg font-medium">{destination.avg_cost_fcfa.toLocaleString()} FCFA</p>
                </div>
              )}

              {destination.how_to_get_there && (
                <div>
                  <p className="text-xs text-neutral-400 mb-1 inline-flex items-center gap-1"><Navigation size={12} />{t("explore.fromCity", "From")} {destination.how_to_get_there.from}</p>
                  <p className="text-sm">
                    ~{destination.how_to_get_there.distance_km} km
                    {destination.how_to_get_there.duration_minutes != null &&
                      ` (~${Math.floor(destination.how_to_get_there.duration_minutes / 60)}h${destination.how_to_get_there.duration_minutes % 60}m)`}
                  </p>
                </div>
              )}

              <a
                href={`https://www.openstreetmap.org/?mlat=${destination.latitude}&mlon=${destination.longitude}#map=14/${destination.latitude}/${destination.longitude}`}
                target="_blank"
                rel="noreferrer"
                className="block text-center rounded-xl bg-canopy-500 hover:bg-canopy-700 text-white text-sm font-medium py-2"
              >
                {t("places.viewOnMap", "View on map")}
              </a>
            </div>
          </div>
        </div>
      </div>

      <AnimatedCanopyBackground variant="fixed" className="opacity-40" />
    </div>
  );
}
