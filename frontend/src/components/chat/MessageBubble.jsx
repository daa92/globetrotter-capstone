import { useState } from "react";
import { Check, CheckCheck, Pencil, Trash2, Download } from "lucide-react";

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function MediaContent({ message }) {
  if (message.type === "image") {
    return (
      <a href={message.media_url} target="_blank" rel="noreferrer">
        <img src={message.media_url} alt={message.file_name || "image"} className="max-h-64 w-auto rounded-lg object-cover" />
      </a>
    );
  }
  if (message.type === "video") {
    return <video src={message.media_url} controls className="max-h-64 w-auto rounded-lg" />;
  }
  if (message.type === "audio") {
    return <audio src={message.media_url} controls className="max-w-full" />;
  }
  return (
    <a
      href={message.media_url}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-2 rounded-lg bg-black/5 dark:bg-white/10 px-3 py-2 text-sm underline"
    >
      <Download size={16} />
      {message.file_name || "Attachment"}
    </a>
  );
}

export default function MessageBubble({ message, isMine, showSender, isGroup, readByOthers, onEdit, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.text || "");
  const [menuOpen, setMenuOpen] = useState(false);

  const saveEdit = () => {
    if (draft.trim() && draft.trim() !== message.text) onEdit(message.id, draft.trim());
    setEditing(false);
  };

  if (message.deleted) {
    return (
      <div className={`flex ${isMine ? "justify-end" : "justify-start"} px-2 py-0.5`}>
        <div className="max-w-[75%] rounded-2xl bg-neutral-100 dark:bg-neutral-800 px-3 py-2 text-xs italic text-neutral-400">
          This message was deleted
        </div>
      </div>
    );
  }

  return (
    <div className={`group flex ${isMine ? "justify-end" : "justify-start"} px-2 py-0.5`}>
      <div className={`relative max-w-[75%] ${isMine ? "items-end" : "items-start"} flex flex-col`}>
        {showSender && !isMine && isGroup && (
          <span className="mb-0.5 ml-1 text-xs font-semibold text-teal-700 dark:text-teal-400">{message.sender}</span>
        )}

        <div
          className={`rounded-2xl px-3 py-2 text-sm shadow-sm ${
            isMine
              ? "bg-teal-700 text-white rounded-br-sm"
              : "bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 rounded-bl-sm border border-neutral-200 dark:border-neutral-700"
          }`}
        >
          {message.media_url && <div className="mb-1">{<MediaContent message={message} />}</div>}

          {editing ? (
            <div className="flex items-center gap-1">
              <input
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && saveEdit()}
                className="rounded-md bg-white/90 text-neutral-900 px-2 py-1 text-sm outline-none"
              />
              <button onClick={saveEdit} className="text-xs font-semibold underline">
                Save
              </button>
              <button onClick={() => setEditing(false)} className="text-xs underline opacity-80">
                Cancel
              </button>
            </div>
          ) : (
            message.text && <p className="whitespace-pre-wrap break-words">{message.text}</p>
          )}

          <div className={`mt-1 flex items-center gap-1 text-[10px] ${isMine ? "text-teal-100" : "text-neutral-400"}`}>
            {formatTime(message.created_at)}
            {message.edited_at && <span>· edited</span>}
            {isMine && (readByOthers ? <CheckCheck size={13} /> : <Check size={13} />)}
          </div>
        </div>

        {isMine && !editing && (
          <div className="absolute -top-3 right-1 hidden group-hover:flex items-center gap-1 rounded-full bg-white dark:bg-neutral-900 shadow px-1 py-0.5 border border-neutral-200 dark:border-neutral-700">
            {message.type === "text" && (
              <button onClick={() => setEditing(true)} aria-label="Edit message" className="p-1 text-neutral-500 hover:text-teal-700">
                <Pencil size={12} />
              </button>
            )}
            <button onClick={() => onDelete(message.id)} aria-label="Delete message" className="p-1 text-neutral-500 hover:text-red-600">
              <Trash2 size={12} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
