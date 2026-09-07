import { useRef, useState } from "react";
import { Paperclip, Send, X } from "lucide-react";

export default function MessageComposer({ onSendText, onSendMedia, onTyping, sending }) {
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (file) {
      await onSendMedia(file, text.trim() || undefined);
      setFile(null);
      setText("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    if (!text.trim()) return;
    const value = text.trim();
    setText("");
    await onSendText(value);
  };

  return (
    <form onSubmit={handleSubmit} className="border-t border-neutral-200 dark:border-neutral-700 p-2 sm:p-3">
      {file && (
        <div className="mb-2 flex items-center gap-2 rounded-lg bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 text-xs">
          <span className="flex-1 truncate">{file.name}</span>
          <button type="button" onClick={() => setFile(null)} aria-label="Remove attachment">
            <X size={14} />
          </button>
        </div>
      )}
      <div className="flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Attach a file"
          className="rounded-full p-2 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 shrink-0"
        >
          <Paperclip size={18} />
        </button>
        <input
          type="text"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            onTyping?.();
          }}
          placeholder={file ? "Add a caption…" : "Type a message…"}
          className="flex-1 min-w-0 rounded-full border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-4 py-2 text-sm outline-none focus:border-teal-600"
        />
        <button
          type="submit"
          disabled={sending || (!text.trim() && !file)}
          aria-label="Send message"
          className="rounded-full bg-teal-700 p-2.5 text-white hover:bg-teal-800 transition disabled:opacity-50 shrink-0"
        >
          <Send size={16} />
        </button>
      </div>
    </form>
  );
}
