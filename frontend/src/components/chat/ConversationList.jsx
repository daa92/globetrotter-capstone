import { SquarePen } from "lucide-react";
import UserAvatar from "../layout/UserAvatar";
import { conversationDisplay, messagePreview } from "../../utils/chat";

function formatWhen(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  return sameDay
    ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString([], { day: "2-digit", month: "short" });
}

export default function ConversationList({ conversations, activeId, currentUsername, onSelect, onNewChat, loading }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-700 px-4 py-3">
        <h1 className="text-lg font-bold">Chats</h1>
        <button
          onClick={onNewChat}
          aria-label="New chat"
          className="rounded-full bg-teal-700 p-2 text-white hover:bg-teal-800 transition"
        >
          <SquarePen size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && <p className="px-4 py-6 text-sm text-neutral-400">Loading chats…</p>}
        {!loading && conversations.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-neutral-400">
            No conversations yet. Tap the pencil to message someone.
          </div>
        )}
        {conversations.map((c) => {
          const { name, avatarUser, subtitle } = conversationDisplay(c, currentUsername);
          return (
            <button
              key={c.id}
              onClick={() => onSelect(c.id)}
              className={`flex w-full items-center gap-3 px-4 py-3 text-left transition border-b border-neutral-100 dark:border-neutral-800 ${
                activeId === c.id ? "bg-teal-50 dark:bg-teal-950/30" : "hover:bg-neutral-50 dark:hover:bg-neutral-800/60"
              }`}
            >
              <UserAvatar user={avatarUser} size={44} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold">{name}</span>
                  <span className="shrink-0 text-[11px] text-neutral-400">{formatWhen(c.last_message?.created_at || c.created_at)}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs text-neutral-500 dark:text-neutral-400">
                    {c.last_message ? `${c.last_message.sender === currentUsername ? "You: " : ""}${messagePreview(c.last_message)}` : subtitle || "No messages yet"}
                  </span>
                  {c.unread_count > 0 && (
                    <span className="shrink-0 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-teal-700 px-1.5 text-[10px] font-bold text-white">
                      {c.unread_count > 99 ? "99+" : c.unread_count}
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
