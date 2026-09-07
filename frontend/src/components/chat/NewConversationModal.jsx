import { useState } from "react";
import { X } from "lucide-react";
import * as api from "../../api/client";
import { ApiError } from "../../api/client";
import UserPicker from "./UserPicker";

export default function NewConversationModal({ accessToken, currentUsername, onClose, onCreated }) {
  const [mode, setMode] = useState("direct"); // "direct" | "group"
  const [selected, setSelected] = useState([]);
  const [groupName, setGroupName] = useState("");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const toggle = (u) => {
    setSelected((prev) => (prev.some((s) => s.username === u.username) ? prev.filter((s) => s.username !== u.username) : [...prev, u]));
  };

  const handleCreate = async () => {
    setError(null);
    if (selected.length === 0) {
      setError("Pick at least one person");
      return;
    }
    if (mode === "group" && !groupName.trim()) {
      setError("Give the group a name");
      return;
    }
    setSaving(true);
    try {
      const conv =
        mode === "direct"
          ? await api.createDirectConversation(accessToken, selected[0].username)
          : await api.createGroupConversation(
              accessToken,
              groupName.trim(),
              selected.map((u) => u.username)
            );
      onCreated(conv);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't start the chat");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 px-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-2xl bg-white dark:bg-neutral-900 p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">New chat</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-full p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800">
            <X size={18} />
          </button>
        </div>

        <div className="mt-3 flex gap-2 text-sm">
          <button
            onClick={() => {
              setMode("direct");
              setSelected(selected.slice(0, 1));
            }}
            className={`flex-1 rounded-full py-1.5 font-semibold border ${
              mode === "direct" ? "bg-teal-700 text-white border-teal-700" : "border-neutral-300 dark:border-neutral-600"
            }`}
          >
            Direct message
          </button>
          <button
            onClick={() => setMode("group")}
            className={`flex-1 rounded-full py-1.5 font-semibold border ${
              mode === "group" ? "bg-teal-700 text-white border-teal-700" : "border-neutral-300 dark:border-neutral-600"
            }`}
          >
            New group
          </button>
        </div>

        {mode === "group" && (
          <input
            type="text"
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            placeholder="Group name"
            className="mt-3 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm outline-none focus:border-teal-600"
          />
        )}

        <div className="mt-3">
          <UserPicker
            accessToken={accessToken}
            excludeUsernames={[currentUsername]}
            selected={selected}
            onToggle={(u) => {
              if (mode === "direct") {
                setSelected([u]);
              } else {
                toggle(u);
              }
            }}
          />
        </div>

        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

        <button
          onClick={handleCreate}
          disabled={saving}
          className="mt-4 w-full rounded-full bg-teal-700 py-2 text-sm font-semibold text-white hover:bg-teal-800 transition disabled:opacity-60"
        >
          {saving ? "Starting…" : mode === "direct" ? "Start chat" : "Create group"}
        </button>
      </div>
    </div>
  );
}
