import { useEffect, useRef } from "react";
import { ArrowLeft, Info } from "lucide-react";
import UserAvatar from "../layout/UserAvatar";
import MessageBubble from "./MessageBubble";
import MessageComposer from "./MessageComposer";
import { conversationDisplay } from "../../utils/chat";

export default function ChatWindow({
  conversation,
  messages,
  currentUsername,
  onBack,
  onOpenInfo,
  onSendText,
  onSendMedia,
  onEditMessage,
  onDeleteMessage,
  onTyping,
  typingUsers,
  loadingMessages,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, conversation?.id]);

  if (!conversation) {
    return (
      <div className="hidden md:flex h-full flex-1 items-center justify-center text-sm text-neutral-400">
        Select a conversation to start chatting
      </div>
    );
  }

  const { name, avatarUser } = conversationDisplay(conversation, currentUsername);
  const isGroup = conversation.type === "group";
  const typingNames = [...typingUsers].filter((u) => u !== currentUsername);

  return (
    <div className="flex h-full flex-1 flex-col">
      <div className="flex items-center gap-2 border-b border-neutral-200 dark:border-neutral-700 px-3 py-2.5">
        <button onClick={onBack} aria-label="Back to chats" className="md:hidden rounded-full p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800">
          <ArrowLeft size={18} />
        </button>
        <button onClick={onOpenInfo} className="flex min-w-0 flex-1 items-center gap-2 text-left">
          <UserAvatar user={avatarUser} size={36} />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{name}</p>
            {typingNames.length > 0 ? (
              <p className="truncate text-xs text-teal-600 dark:text-teal-400">{typingNames.join(", ")} typing…</p>
            ) : (
              isGroup && <p className="truncate text-xs text-neutral-400">{conversation.members.length} members</p>
            )}
          </div>
        </button>
        <button onClick={onOpenInfo} aria-label="Conversation info" className="rounded-full p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800">
          <Info size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto bg-neutral-50 dark:bg-neutral-950 py-3">
        {loadingMessages && <p className="px-4 text-center text-xs text-neutral-400">Loading messages…</p>}
        {!loadingMessages && messages.length === 0 && (
          <p className="px-4 text-center text-xs text-neutral-400">No messages yet — say hello 👋</p>
        )}
        {messages.map((m, i) => (
          <MessageBubble
            key={m.id}
            message={m}
            isMine={m.sender === currentUsername}
            showSender={i === 0 || messages[i - 1].sender !== m.sender}
            isGroup={isGroup}
            readByOthers={m.read_by && m.read_by.length > 0}
            onEdit={onEditMessage}
            onDelete={onDeleteMessage}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      <MessageComposer onSendText={onSendText} onSendMedia={onSendMedia} onTyping={() => onTyping(conversation.id)} />
    </div>
  );
}
