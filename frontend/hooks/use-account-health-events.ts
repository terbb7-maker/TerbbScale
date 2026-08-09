"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { api } from "@/lib/api";

export function useAccountHealthEvents() {
  const queryClient = useQueryClient();

  useEffect(() => {
    let socket: WebSocket | undefined;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;

    async function connect() {
      try {
        const { ticket } = await api<{ ticket: string }>("/auth/ws-ticket", { method: "POST" });
        if (cancelled) return;
        const endpoint = new URL(process.env.NEXT_PUBLIC_API_URL ?? "/api/v1", window.location.origin);
        endpoint.protocol = endpoint.protocol === "https:" ? "wss:" : "ws:";
        endpoint.pathname = `${endpoint.pathname.replace(/\/$/, "")}/ws/dashboard`;
        endpoint.search = new URLSearchParams({ ticket }).toString();
        socket = new WebSocket(endpoint);
        socket.onmessage = (message) => {
          const payload = JSON.parse(message.data) as { event?: string };
          if (payload.event === "account.health_updated" || payload.event?.startsWith("publication.")) {
            void queryClient.invalidateQueries({ queryKey: ["accounts"] });
            void queryClient.invalidateQueries({ queryKey: ["account-health"] });
            void queryClient.invalidateQueries({ queryKey: ["notifications"] });
          }
        };
        socket.onclose = () => {
          if (!cancelled) reconnectTimer = setTimeout(connect, 5000);
        };
      } catch {
        if (!cancelled) reconnectTimer = setTimeout(connect, 10000);
      }
    }

    void connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [queryClient]);
}
