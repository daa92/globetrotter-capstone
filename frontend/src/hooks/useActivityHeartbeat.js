/**
 * src/hooks/useActivityHeartbeat.js
 *
 * Fixes the earnings bug where usage bonuses never accrued: the backend
 * has always correctly computed "$0.50/day for >=5 active minutes" from
 * heartbeat records (see app/routers/earnings.py), and the API call to
 * report activity has existed in api/client.js this whole time — but
 * nothing in the app ever actually called it. Zero heartbeats in means
 * zero qualifying days out, no matter how correct the earnings math is.
 *
 * Sends a heartbeat every 60s while the user is logged in AND the tab is
 * actually visible/focused (skips silently while backgrounded/minimized,
 * so "active" means what it says). 60s per tick, comfortably under the
 * backend's 90s anti-abuse cap per call (MAX_HEARTBEAT_INCREMENT_SECONDS),
 * so nothing gets silently truncated — 5 ticks (5 real minutes of the
 * tab being open and focused) is exactly enough to cross the 300s/day
 * threshold.
 *
 * Mount this once, high in the tree (see App.jsx) — it's a no-op
 * whenever nobody's logged in.
 */
import { useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { sendHeartbeat } from "../api/client";

const TICK_SECONDS = 60;

export default function useActivityHeartbeat() {
  const { isAuthenticated, accessToken } = useAuth();
  const tokenRef = useRef(accessToken);
  tokenRef.current = accessToken;

  useEffect(() => {
    if (!isAuthenticated) return undefined;

    const tick = () => {
      if (document.visibilityState !== "visible") return; // don't count backgrounded time
      const token = tokenRef.current;
      if (!token) return;
      sendHeartbeat(token, TICK_SECONDS).catch(() => {
        // Best-effort — a missed heartbeat just means slightly slower
        // earnings accrual, not something worth surfacing to the user.
      });
    };

    const interval = setInterval(tick, TICK_SECONDS * 1000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);
}
