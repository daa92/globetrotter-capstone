import { useEffect, useState } from "react";
import * as api from "../../api/client";
import UserAvatar from "../layout/UserAvatar";

/**
 * Debounced username search with optional multi-select — used for
 * "start a new chat", "new group", and "add members to a group".
 */
export default function UserPicker({ accessToken, excludeUsernames = [], selected, onToggle, multi = true }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const found = await api.searchChatUsers(accessToken, query.trim());
        if (!cancelled) setResults(found.filter((u) => !excludeUsernames.includes(u.username)));
      } catch {
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, accessToken]);

  const isSelected = (username) => selected?.some((s) => s.username === username);

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by username…"
        className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm outline-none focus:border-teal-600"
      />

      {multi && selected?.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {selected.map((u) => (
            <span
              key={u.username}
              className="flex items-center gap-1 rounded-full bg-teal-50 dark:bg-teal-950/40 text-teal-800 dark:text-teal-300 pl-1 pr-2 py-0.5 text-xs font-medium"
            >
              <UserAvatar user={u} size={18} />
              {u.username}
              <button onClick={() => onToggle(u)} className="ml-0.5 text-teal-600 hover:text-teal-900" aria-label={`Remove ${u.username}`}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="mt-2 max-h-52 overflow-y-auto rounded-lg border border-neutral-200 dark:border-neutral-700 divide-y divide-neutral-100 dark:divide-neutral-800">
        {loading && <p className="px-3 py-2 text-xs text-neutral-400">Searching…</p>}
        {!loading && query.trim() && results.length === 0 && (
          <p className="px-3 py-2 text-xs text-neutral-400">No users found</p>
        )}
        {results.map((u) => (
          <button
            key={u.username}
            type="button"
            onClick={() => onToggle(u)}
            className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 ${
              isSelected(u.username) ? "bg-teal-50 dark:bg-teal-950/30" : ""
            }`}
          >
            <UserAvatar user={u} size={26} />
            <span className="flex-1 truncate">{u.username}</span>
            {isSelected(u.username) && <span className="text-teal-600 text-xs font-semibold">Selected</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
