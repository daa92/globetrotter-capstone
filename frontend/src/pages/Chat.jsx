import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import * as api from "../api/client";
import { ApiError } from "../api/client";
import useChatSocket from "../hooks/useChatSocket";
import ConversationList from "../components/chat/ConversationList";
import ChatWindow from "../components/chat/ChatWindow";
import NewConversationModal from "../components/chat/NewConversationModal";
import ConversationInfoPanel from "../components/chat/ConversationInfoPanel";

function upsertConversation(list, conversation) {
  const idx = list.findIndex((c) => c.id === conversation.id);
  const next = idx === -1 ? [conversation, ...list] : list.map((c) => (c.id === conversation.id ? conversation : c));
  return [...next].sort((a, b) => {
    const at = a.last_message?.created_at || a.created_at;
    const bt = b.last_message?.created_at || b.created_at;
    return bt.localeCompare(at);
  });
}

function upsertMessage(list, message) {
  const idx = list.findIndex((m) => m.id === message.id);
  if (idx === -1) return [...list, message].sort((a, b) => a.created_at.localeCompare(b.created_at));
  const next = [...list];
  next[idx] = message;
  return next;
}

export default function Chat() {
  const { user, accessToken, isAuthenticated, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const { conversationId } = useParams();

  const [conversations, setConversations] = useState([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [showNewChat, setShowNewChat] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [error, setError] = useState(null);
  const [typingByConversation, setTypingByConversation] = useState({});

  const activeId = conversationId || null;
  const activeConversation = conversations.find((c) => c.id === activeId) || null;
  const typingTimers = useRef({});

  const loadConversations = useCallback(async () => {
    try {
      const list = await api.listConversations(accessToken);
      setConversations(list);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't load your chats");
    } finally {
      setLoadingConversations(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (isAuthenticated) loadConversations();
  }, [isAuthenticated, loadConversations]);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingMessages(true);
    api
      .listMessages(accessToken, activeId, { limit: 100 })
      .then((msgs) => !cancelled && setMessages(msgs))
      .catch(() => !cancelled && setMessages([]))
      .finally(() => !cancelled && setLoadingMessages(false));
    api.markConversationRead(accessToken, activeId).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [activeId, accessToken]);

  const handleSocketEvent = useCallback(
    (data) => {
      switch (data.event) {
        case "message.new":
        case "message.updated":
        case "message.deleted": {
          if (data.conversation_id === activeId) {
            setMessages((prev) => upsertMessage(prev, data.message));
            if (data.event === "message.new" && data.message.sender !== user?.username) {
              api.markConversationRead(accessToken, activeId).catch(() => {});
            }
          }
          setConversations((prev) =>
            prev.map((c) =>
              c.id === data.conversation_id
                ? {
                    ...c,
                    last_message: data.message,
                    unread_count:
                      data.event === "message.new" && data.message.sender !== user?.username && data.conversation_id !== activeId
                        ? (c.unread_count || 0) + 1
                        : c.unread_count,
                  }
                : c
            )
          );
          break;
        }
        case "conversation.new":
        case "conversation.updated": {
          setConversations((prev) => upsertConversation(prev, data.conversation));
          break;
        }
        case "conversation.deleted": {
          setConversations((prev) => prev.filter((c) => c.id !== data.conversation_id));
          if (data.conversation_id === activeId) navigate("/chat");
          break;
        }
        case "conversation.read": {
          if (data.conversation_id === activeId) {
            api
              .listMessages(accessToken, activeId, { limit: 100 })
              .then((msgs) => setMessages(msgs))
              .catch(() => {});
          }
          break;
        }
        case "typing": {
          const key = data.conversation_id;
          setTypingByConversation((prev) => ({ ...prev, [key]: new Set([...(prev[key] || []), data.username]) }));
          clearTimeout(typingTimers.current[`${key}:${data.username}`]);
          typingTimers.current[`${key}:${data.username}`] = setTimeout(() => {
            setTypingByConversation((prev) => {
              const next = new Set(prev[key] || []);
              next.delete(data.username);
              return { ...prev, [key]: next };
            });
          }, 3000);
          break;
        }
        default:
          break;
      }
    },
    [activeId, accessToken, user?.username, navigate]
  );

  const { sendTyping } = useChatSocket(accessToken, handleSocketEvent);

  const handleSelect = (id) => navigate(`/chat/${id}`);
  const handleBack = () => navigate("/chat");

  const handleSendText = async (text) => {
    if (!activeId) return;
    try {
      const msg = await api.sendMessage(accessToken, activeId, text);
      setMessages((prev) => upsertMessage(prev, msg));
      setConversations((prev) => prev.map((c) => (c.id === activeId ? { ...c, last_message: msg } : c)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Message failed to send");
    }
  };

  const handleSendMedia = async (file, caption) => {
    if (!activeId) return;
    try {
      const msg = await api.sendMediaMessage(accessToken, activeId, file, caption);
      setMessages((prev) => upsertMessage(prev, msg));
      setConversations((prev) => prev.map((c) => (c.id === activeId ? { ...c, last_message: msg } : c)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Attachment failed to send");
    }
  };

  const handleEditMessage = async (messageId, text) => {
    try {
      const msg = await api.editMessage(accessToken, messageId, text);
      setMessages((prev) => upsertMessage(prev, msg));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't edit that message");
    }
  };

  const handleDeleteMessage = async (messageId) => {
    try {
      const msg = await api.deleteMessage(accessToken, messageId);
      setMessages((prev) => upsertMessage(prev, msg));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't delete that message");
    }
  };

  const handleCreated = (conv) => {
    setConversations((prev) => upsertConversation(prev, conv));
    setShowNewChat(false);
    navigate(`/chat/${conv.id}`);
  };

  const handleConversationChanged = (conv) => {
    setConversations((prev) => upsertConversation(prev, conv));
  };

  const handleConversationDeleted = () => {
    setShowInfo(false);
    navigate("/chat");
    loadConversations();
  };

  if (authLoading) return null;
  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center">
        <p className="text-neutral-500">Log in to use chat.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-64px)] max-w-6xl overflow-hidden border-x border-neutral-200 dark:border-neutral-800">
      <div className={`w-full md:w-80 md:shrink-0 border-r border-neutral-200 dark:border-neutral-700 ${activeId ? "hidden md:block" : "block"}`}>
        <ConversationList
          conversations={conversations}
          activeId={activeId}
          currentUsername={user.username}
          onSelect={handleSelect}
          onNewChat={() => setShowNewChat(true)}
          loading={loadingConversations}
        />
      </div>

      <div className={`flex-1 ${activeId ? "block" : "hidden md:block"}`}>
        <ChatWindow
          conversation={activeConversation}
          messages={messages}
          currentUsername={user.username}
          onBack={handleBack}
          onOpenInfo={() => setShowInfo(true)}
          onSendText={handleSendText}
          onSendMedia={handleSendMedia}
          onEditMessage={handleEditMessage}
          onDeleteMessage={handleDeleteMessage}
          onTyping={sendTyping}
          typingUsers={typingByConversation[activeId] || new Set()}
          loadingMessages={loadingMessages}
        />
      </div>

      {error && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-red-600 px-4 py-2 text-xs font-medium text-white shadow-lg" onClick={() => setError(null)}>
          {error}
        </div>
      )}

      {showNewChat && (
        <NewConversationModal
          accessToken={accessToken}
          currentUsername={user.username}
          onClose={() => setShowNewChat(false)}
          onCreated={handleCreated}
        />
      )}

      {showInfo && activeConversation && (
        <ConversationInfoPanel
          accessToken={accessToken}
          currentUsername={user.username}
          conversation={activeConversation}
          onClose={() => setShowInfo(false)}
          onChanged={handleConversationChanged}
          onDeleted={handleConversationDeleted}
        />
      )}
    </div>
  );
}
