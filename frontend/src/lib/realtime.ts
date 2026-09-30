"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Live updates over WebSocket.
 *
 * Events are treated purely as cache-invalidation hints — we refetch through the
 * REST API rather than trusting the payload, so a missed, duplicated or
 * out-of-order event can never leave the UI showing wrong data. If the socket
 * can't connect at all the app degrades to normal fetch-on-navigate behaviour.
 */
type Event = { type: string; issue_key?: string; project_id?: number };

const MAX_ATTEMPTS = 6;

function candidateUrls(): string[] {
  if (typeof window === "undefined") return [];
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  if (explicit) return [explicit];

  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const sameOrigin = `${proto}//${window.location.host}/api/ws`;
  // Dev convenience: when the frontend is hit directly on :3000 the Next proxy
  // may not upgrade WebSockets, so fall back to the backend's own port.
  // (Cookies are port-agnostic, so the session still authenticates.)
  const direct = `${proto}//${window.location.hostname}:8000/api/ws`;
  return window.location.port === "3000" ? [sameOrigin, direct] : [sameOrigin];
}

export function useRealtime(enabled: boolean) {
  const qc = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const urlIndexRef = useRef(0);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;
    const urls = candidateUrls();
    if (urls.length === 0) return;

    let closed = false;
    let retryTimer: ReturnType<typeof setTimeout>;
    let pingTimer: ReturnType<typeof setInterval>;

    const connect = () => {
      if (closed || attemptsRef.current >= MAX_ATTEMPTS) return;
      const url = urls[Math.min(urlIndexRef.current, urls.length - 1)];
      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch {
        return;
      }
      socketRef.current = ws;

      ws.onopen = () => {
        attemptsRef.current = 0;
        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, 30_000);
      };

      ws.onmessage = (e) => {
        let event: Event;
        try {
          event = JSON.parse(e.data);
        } catch {
          return;
        }
        handle(event);
      };

      ws.onclose = () => {
        clearInterval(pingTimer);
        if (closed) return;
        attemptsRef.current += 1;
        // Try the next candidate URL after the first failure.
        if (attemptsRef.current === 1 && urls.length > 1) urlIndexRef.current = 1;
        const backoff = Math.min(1000 * 2 ** attemptsRef.current, 30_000);
        retryTimer = setTimeout(connect, backoff);
      };

      ws.onerror = () => ws.close();
    };

    const handle = (event: Event) => {
      switch (event.type) {
        case "issue.created":
        case "issue.updated":
        case "issue.moved":
        case "issue.archived":
          qc.invalidateQueries({ queryKey: ["board"] });
          qc.invalidateQueries({ queryKey: ["issues"] });
          qc.invalidateQueries({ queryKey: ["my-issues"] });
          qc.invalidateQueries({ queryKey: ["dashboard"] });
          if (event.issue_key) {
            qc.invalidateQueries({ queryKey: ["issue", event.issue_key] });
            qc.invalidateQueries({ queryKey: ["activity", event.issue_key] });
          }
          break;
        case "comment.added":
          if (event.issue_key) {
            qc.invalidateQueries({ queryKey: ["comments", event.issue_key] });
            qc.invalidateQueries({ queryKey: ["activity", event.issue_key] });
            qc.invalidateQueries({ queryKey: ["issue", event.issue_key] });
          }
          break;
        case "notification":
          qc.invalidateQueries({ queryKey: ["notifications"] });
          qc.invalidateQueries({ queryKey: ["unread"] });
          break;
      }
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(retryTimer);
      clearInterval(pingTimer);
      socketRef.current?.close();
    };
  }, [enabled, qc]);
}
