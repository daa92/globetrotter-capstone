import { MapPin } from "lucide-react";
import { useTranslation } from "react-i18next";

const ALL_TAGS = ["beach", "hiking", "culture", "history", "wildlife", "nightlife", "waterfall", "city", "nature"];
const MAX_BUDGET_SLIDER = 100000;

export default function FilterPanel({
  selectedTags,
  onToggleTag,
  maxBudget,
  onMaxBudgetChange,
  budgetUnlimited,
  onToggleBudgetUnlimited,
  distanceEnabled,
  onToggleDistance,
  maxDistanceKm,
  onMaxDistanceChange,
  geoStatus,
  poiCategories,
  selectedPoiCategories,
  onTogglePoiCategory,
}) {
  const { t } = useTranslation();

  return (
    <div className="mt-4 flex flex-wrap items-start gap-6 rounded-2xl border border-neutral-200 dark:border-neutral-700 p-4">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">{t("explore.type")}</p>
        <div className="flex flex-wrap gap-2 max-w-xs">
          {ALL_TAGS.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => onToggleTag(tag)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                selectedTags.includes(tag)
                  ? "text-white border-transparent"
                  : "border-neutral-300 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300"
              }`}
              style={selectedTags.includes(tag) ? { backgroundColor: "#127C71" } : {}}
            >
              {t(`tags.${tag}`, tag)}
            </button>
          ))}
        </div>
      </div>

      {poiCategories.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">{t("explore.nearbyPlaces")}</p>
          <div className="flex flex-wrap gap-2 max-w-sm">
            {poiCategories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => onTogglePoiCategory(cat)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                  selectedPoiCategories.includes(cat)
                    ? "text-white border-transparent"
                    : "border-neutral-300 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300"
                }`}
                style={selectedPoiCategories.includes(cat) ? { backgroundColor: "#C9975C" } : {}}
              >
                {t(`poiCategories.${cat}`, cat)}
              </button>
            ))}
          </div>
          {selectedPoiCategories.length > 0 && !distanceEnabled && (
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">{t("explore.enableNearMeForPoi")}</p>
          )}
        </div>
      )}

      <div className="min-w-[180px]">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400">
            {budgetUnlimited ? t("explore.budgetAny") : t("explore.budget", { amount: maxBudget.toLocaleString() })}
          </p>
        </div>
        <input
          type="range"
          min={0}
          max={MAX_BUDGET_SLIDER}
          step={1000}
          value={maxBudget}
          disabled={budgetUnlimited}
          onChange={(e) => onMaxBudgetChange(Number(e.target.value))}
          className="w-full accent-teal-700 disabled:opacity-40"
        />
        <label className="mt-1 flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400">
          <input type="checkbox" checked={budgetUnlimited} onChange={onToggleBudgetUnlimited} />
          {t("explore.anyBudget")}
        </label>
      </div>

      <div className="min-w-[200px]">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">{t("explore.distance")}</p>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={distanceEnabled} onChange={onToggleDistance} />
          <MapPin className="h-4 w-4 text-neutral-400" />
          {t("explore.nearMe")}
        </label>
        {distanceEnabled && (
          <>
            {geoStatus === "denied" && <p className="mt-1 text-xs text-red-500">{t("explore.locationDenied")}</p>}
            {geoStatus === "pending" && <p className="mt-1 text-xs text-neutral-400">{t("explore.gettingLocation")}</p>}
            {geoStatus === "ok" && (
              <div className="mt-2">
                <p className="text-xs text-neutral-500">{t("explore.within", { km: maxDistanceKm })}</p>
                <input
                  type="range"
                  min={5}
                  max={1000}
                  step={5}
                  value={maxDistanceKm}
                  onChange={(e) => onMaxDistanceChange(Number(e.target.value))}
                  className="w-full accent-teal-700"
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
