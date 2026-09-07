import { useEffect, useRef } from "react";
import { chatWebSocketUrl } from "../api/client";

/**
 * Keeps a live WebSocket connection to /chat/ws open while the caller is
 * mounted, and calls `onEvent(data)` for every message the server pushes
 * (new/edited/deleted messages, conversation updates, typing, read
 * receipts — see app/routers/chat.py for the full event list).
 *
 * Auto-reconnects with a short backoff if the connection drops (flaky
 * mobile networks, server restart, etc.) rather than leaving the chat
 * silently stale.
 */
export default function useChatSocket(accessToken, onEvent) {
  const socketRef = useRef(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!accessToken) return undefined;

    let cancelled = false;
    let reconnectTimer = null;
    let attempt = 0;

    const connect = () => {
      if (cancelled) return;
      const socket = new WebSocket(chatWebSocketUrl(accessToken));
      socketRef.current = socket;

      socket.onopen = () => {
        attempt = 0;
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onEventRef.current?.(data);
        } catch {
          // Ignore malformed frames rather than crashing the chat UI.
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        attempt += 1;
        const delay = Math.min(1000 * attempt, 8000);
        reconnectTimer = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [accessToken]);

  const sendTyping = (conversationId) => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ event: "typing", conversation_id: conversationId }));
    }
  };

  return { sendTyping };
}
