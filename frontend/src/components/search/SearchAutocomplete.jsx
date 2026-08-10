import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Search } from "lucide-react";

/**
 * As you type, suggests matching destination names AND matching tags
 * (e.g. typing "f" suggests both destinations with "f" in the name and
 * the "forest"/tag-style matches) — computed client-side against the
 * already-fetched catalogue, so suggestions appear instantly with no
 * network round-trip per keystroke.
 */
export default function SearchAutocomplete({ destinations, value, onChange, onSelectDestination, placeholder }) {
  const { t } = useTranslation();
  const [focused, setFocused] = useState(false);

  const suggestions = useMemo(() => {
    const q = value.trim().toLowerCase();
    if (q.length === 0) return [];

    const nameMatches = destinations
      .filter((d) => d.name.toLowerCase().includes(q))
      .map((d) => ({ type: "destination", label: d.name, destination: d }));

    const matchingTags = new Set();
    destinations.forEach((d) => d.tags.forEach((tag) => {
      const translated = t(`tags.${tag}`, tag).toLowerCase();
      if (tag.toLowerCase().includes(q) || translated.includes(q)) matchingTags.add(tag);
    }));
    const tagMatches = [...matchingTags].map((tag) => ({ type: "tag", label: t(`tags.${tag}`, tag), rawTag: tag }));

    return [...nameMatches.slice(0, 5), ...tagMatches.slice(0, 4)];
  }, [value, destinations, t]);

  return (
    <div className="relative flex-1 min-w-[220px]">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)} // allow the click on a suggestion to register first
          placeholder={placeholder}
          className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent py-2 pl-9 pr-4 focus:outline-none focus:ring-2 focus:ring-teal-600"
        />
      </div>

      {focused && suggestions.length > 0 && (
        <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-lg">
          {suggestions.map((s, i) => (
            <button
              key={`${s.type}-${s.label}-${i}`}
              type="button"
              onMouseDown={() => {
                if (s.type === "destination") {
                  onSelectDestination(s.destination);
                } else {
                  onChange(s.label);
                }
              }}
              className="flex w-full items-center justify-between px-4 py-2 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-700"
            >
              <span>{s.label}</span>
              {s.type === "tag" && (
                <span className="text-xs text-neutral-400">{t("explore.tag")}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
