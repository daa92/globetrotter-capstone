import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import { Check, ChevronRight, ChevronLeft, Trash2, Calendar, Sparkles, MapPin } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import AnimatedCanopyBackground from "../components/layout/AnimatedCanopyBackground";
import DestinationImage from "../components/destinations/DestinationImage";
import { createItinerary, deleteItinerary, listItineraries, searchDestinations, ApiError } from "../api/client";

const VIBES = [
  "beach", "hiking", "culture", "history", "wildlife", "nightlife", "waterfall",
  "nature", "relaxation", "adventure", "mountain", "food", "shopping",
];

const DATE_PRESETS = [
  { key: "weekend", days: 2 },
  { key: "week", days: 7 },
  { key: "twoWeeks", days: 14 },
];

function todayPlus(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

// --- Step 1: vibe chips --------------------------------------------------

function VibeStep({ selected, onToggle, onNext }) {
  const { t } = useTranslation();
  return (
    <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}>
      <h2 className="font-display text-xl font-semibold mb-1">{t("itineraries.vibeTitle", "What's your vibe?")}</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-5">{t("itineraries.vibeSubtitle", "Pick as many as you like — we'll narrow down destinations for you.")}</p>

      <div className="flex flex-wrap gap-2">
        {VIBES.map((tag) => (
          <motion.button
            key={tag}
            type="button"
            whileTap={{ scale: 0.94 }}
            onClick={() => onToggle(tag)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              selected.includes(tag)
                ? "bg-canopy-500 text-white shadow-lg shadow-canopy-500/30"
                : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300"
            }`}
          >
            {t(`tags.${tag}`, tag)}
          </motion.button>
        ))}
      </div>

      <button
        onClick={onNext}
        className="mt-8 inline-flex items-center gap-1.5 rounded-full bg-canopy-500 hover:bg-canopy-700 text-white px-6 py-2.5 text-sm font-semibold"
      >
        {t("itineraries.next", "Next")} <ChevronRight size={16} />
      </button>
    </motion.div>
  );
}

// --- Step 2: destination picker -------------------------------------------

function DestinationStep({ destinations, vibes, selected, onToggle, onBack, onNext }) {
  const { t } = useTranslation();
  const filtered = useMemo(() => {
    if (vibes.length === 0) return destinations;
    const withMatch = destinations.filter((d) => d.tags?.some((tag) => vibes.includes(tag)));
    return withMatch.length > 0 ? withMatch : destinations; // never leave the picker empty
  }, [destinations, vibes]);

  return (
    <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}>
      <h2 className="font-display text-xl font-semibold mb-1">{t("itineraries.destTitle", "Pick your destinations")}</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-5">
        {t("itineraries.destSubtitle", "{{count}} selected", { count: selected.length })}
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-[50vh] overflow-y-auto pr-1">
        {filtered.map((d) => {
          const isSelected = selected.includes(d.id);
          return (
            <motion.button
              key={d.id}
              type="button"
              whileTap={{ scale: 0.96 }}
              onClick={() => onToggle(d.id)}
              className="relative rounded-xl overflow-hidden text-left group"
            >
              <DestinationImage destination={d} className="h-24 w-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
              <span className="absolute bottom-1.5 left-2 right-2 text-white text-xs font-medium line-clamp-1">{d.name}</span>
              <AnimatePresence>
                {isSelected && (
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0, opacity: 0 }}
                    className="absolute top-1.5 right-1.5 h-6 w-6 rounded-full bg-canopy-500 text-white flex items-center justify-center"
                  >
                    <Check size={14} />
                  </motion.div>
                )}
              </AnimatePresence>
              <div className={`absolute inset-0 border-2 rounded-xl transition-colors ${isSelected ? "border-canopy-500" : "border-transparent"}`} />
            </motion.button>
          );
        })}
      </div>

      <div className="mt-6 flex gap-2">
        <button onClick={onBack} className="inline-flex items-center gap-1 rounded-full bg-neutral-100 dark:bg-neutral-800 px-5 py-2.5 text-sm font-medium">
          <ChevronLeft size={16} /> {t("itineraries.back", "Back")}
        </button>
        <button
          onClick={onNext}
          disabled={selected.length === 0}
          className="inline-flex items-center gap-1.5 rounded-full bg-canopy-500 hover:bg-canopy-700 disabled:opacity-50 text-white px-6 py-2.5 text-sm font-semibold"
        >
          {t("itineraries.next", "Next")} <ChevronRight size={16} />
        </button>
      </div>
    </motion.div>
  );
}

// --- Step 3: dates + title -------------------------------------------------

function DetailsStep({ title, setTitle, startDate, setStartDate, endDate, setEndDate, suggestedTitle, onBack, onSubmit, creating }) {
  const { t } = useTranslation();

  const applyPreset = (days) => {
    setStartDate(todayPlus(1));
    setEndDate(todayPlus(1 + days));
  };

  return (
    <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}>
      <h2 className="font-display text-xl font-semibold mb-1">{t("itineraries.detailsTitle", "Almost there")}</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-5">{t("itineraries.detailsSubtitle", "Give it a name and pick your dates.")}</p>

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder={suggestedTitle}
        className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-transparent px-4 py-2.5 text-sm font-display text-lg"
      />

      <div className="mt-5">
        <p className="text-xs font-medium text-neutral-500 mb-2 inline-flex items-center gap-1"><Sparkles size={13} />{t("itineraries.quickPick", "Quick pick")}</p>
        <div className="flex gap-2 flex-wrap">
          {DATE_PRESETS.map((p) => (
            <button
              key={p.key}
              type="button"
              onClick={() => applyPreset(p.days)}
              className="rounded-full bg-neutral-100 dark:bg-neutral-800 px-4 py-1.5 text-xs font-medium"
            >
              {t(`itineraries.preset.${p.key}`, p.key)}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-neutral-500 inline-flex items-center gap-1 mb-1"><Calendar size={12} />{t("itineraries.startDate")}</label>
          <input type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="text-xs font-medium text-neutral-500 inline-flex items-center gap-1 mb-1"><Calendar size={12} />{t("itineraries.endDate")}</label>
          <input type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm" />
        </div>
      </div>

      <div className="mt-8 flex gap-2">
        <button onClick={onBack} className="inline-flex items-center gap-1 rounded-full bg-neutral-100 dark:bg-neutral-800 px-5 py-2.5 text-sm font-medium">
          <ChevronLeft size={16} /> {t("itineraries.back", "Back")}
        </button>
        <motion.button
          onClick={onSubmit}
          disabled={creating || !startDate || !endDate}
          whileTap={{ scale: 0.97 }}
          className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-full bg-goldhour-500 hover:brightness-95 disabled:opacity-50 text-canopy-900 px-6 py-2.5 text-sm font-bold"
        >
          {creating ? t("itineraries.creating") : t("itineraries.createBtn", "Create my trip")}
        </motion.button>
      </div>
    </motion.div>
  );
}

// --- Trip cards -------------------------------------------------------------

function TripCard({ trip, destinations, onDelete }) {
  const { t } = useTranslation();
  const cover = destinations.find((d) => d.id === trip.destinations[0]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      className="relative rounded-2xl overflow-hidden shadow-lg h-40"
    >
      {cover ? (
        <DestinationImage destination={cover} className="absolute inset-0 h-full w-full object-cover" />
      ) : (
        <div className="absolute inset-0 bg-canopy-700" />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
      <div className="relative h-full flex flex-col justify-end p-4 text-white">
        <p className="font-display text-lg font-semibold">{trip.title}</p>
        <p className="text-xs text-white/80 inline-flex items-center gap-1 mt-0.5">
          <MapPin size={11} />{t("itineraries.destinationsCount", { count: trip.destinations.length })} · {trip.start_date} → {trip.end_date}
        </p>
      </div>
      <button
        onClick={() => onDelete(trip.id)}
        className="absolute top-2 right-2 rounded-full bg-black/50 hover:bg-red-600 text-white p-1.5"
        aria-label={t("itineraries.delete")}
      >
        <Trash2 size={14} />
      </button>
    </motion.div>
  );
}

// --- Page -------------------------------------------------------------------

const STEPS = ["vibe", "destinations", "details"];

export default function Itineraries() {
  const { t } = useTranslation();
  const { isAuthenticated, accessToken, loading: authLoading } = useAuth();
  const [itineraries, setItineraries] = useState([]);
  const [destinations, setDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [step, setStep] = useState(0);
  const [vibes, setVibes] = useState([]);
  const [selectedDestinations, setSelectedDestinations] = useState([]);
  const [title, setTitle] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [creating, setCreating] = useState(false);
  const [planning, setPlanning] = useState(false);

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

  const toggleVibe = (tag) => setVibes((prev) => (prev.includes(tag) ? prev.filter((x) => x !== tag) : [...prev, tag]));
  const toggleDestination = (id) => setSelectedDestinations((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));

  const suggestedTitle = useMemo(() => {
    const names = destinations.filter((d) => selectedDestinations.includes(d.id)).map((d) => d.name);
    if (names.length === 0) return t("itineraries.tripTitlePlaceholder");
    if (names.length === 1) return `${names[0]} ${t("itineraries.trip", "Trip")}`;
    return `${names[0]} & ${names[1]}${names.length > 2 ? " +" : ""} ${t("itineraries.trip", "Trip")}`;
  }, [destinations, selectedDestinations, t]);

  const resetPlanner = () => {
    setStep(0);
    setVibes([]);
    setSelectedDestinations([]);
    setTitle("");
    setStartDate("");
    setEndDate("");
    setPlanning(false);
  };

  const handleCreate = async () => {
    setError(null);
    setCreating(true);
    try {
      await createItinerary(accessToken, {
        title: title.trim() || suggestedTitle,
        destinations: selectedDestinations,
        start_date: startDate,
        end_date: endDate,
      });
      resetPlanner();
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
      <div className="relative">
        <AnimatedCanopyBackground variant="fixed" className="opacity-70" />
        <section className="relative mx-auto max-w-md px-6 py-24 text-center text-white">
          <h1 className="font-display text-3xl font-bold">{t("itineraries.planTitle")}</h1>
          <p className="mt-2 text-white/70">{t("itineraries.planBody")}</p>
          <Link to="/login" className="mt-6 inline-block rounded-full bg-goldhour-500 text-canopy-900 px-6 py-2.5 font-semibold">
            {t("itineraries.login")}
          </Link>
        </section>
      </div>
    );
  }

  return (
    <div className="relative min-h-[80vh]">
      <AnimatedCanopyBackground variant="fixed" className="opacity-30" />

      <section className="relative mx-auto max-w-4xl px-4 sm:px-6 py-12">
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-display text-3xl font-bold">{t("itineraries.title")}</h1>
          {!planning && (
            <motion.button
              whileTap={{ scale: 0.96 }}
              onClick={() => setPlanning(true)}
              className="inline-flex items-center gap-1.5 rounded-full bg-canopy-500 hover:bg-canopy-700 text-white px-5 py-2.5 text-sm font-semibold shadow-lg shadow-canopy-500/20"
            >
              <Sparkles size={15} />{t("itineraries.planNew", "Plan a new trip")}
            </motion.button>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">{error}</div>
        )}

        <AnimatePresence mode="wait">
          {planning && (
            <motion.div
              key="planner"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-10 rounded-2xl bg-white dark:bg-neutral-900 shadow-xl p-6 overflow-hidden"
            >
              <div className="flex gap-1.5 mb-6">
                {STEPS.map((s, i) => (
                  <div key={s} className={`h-1 flex-1 rounded-full transition-colors ${i <= step ? "bg-canopy-500" : "bg-neutral-200 dark:bg-neutral-700"}`} />
                ))}
              </div>

              <AnimatePresence mode="wait">
                {step === 0 && <VibeStep key="vibe" selected={vibes} onToggle={toggleVibe} onNext={() => setStep(1)} />}
                {step === 1 && (
                  <DestinationStep
                    key="dest"
                    destinations={destinations}
                    vibes={vibes}
                    selected={selectedDestinations}
                    onToggle={toggleDestination}
                    onBack={() => setStep(0)}
                    onNext={() => setStep(2)}
                  />
                )}
                {step === 2 && (
                  <DetailsStep
                    key="details"
                    title={title}
                    setTitle={setTitle}
                    startDate={startDate}
                    setStartDate={setStartDate}
                    endDate={endDate}
                    setEndDate={setEndDate}
                    suggestedTitle={suggestedTitle}
                    onBack={() => setStep(1)}
                    onSubmit={handleCreate}
                    creating={creating}
                  />
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>

        {loading ? (
          <p className="text-neutral-400">{t("itineraries.loading")}</p>
        ) : itineraries.length === 0 && !planning ? (
          <p className="text-neutral-400">{t("itineraries.noTrips")}</p>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {itineraries.map((it) => (
              <TripCard key={it.id} trip={it} destinations={destinations} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
