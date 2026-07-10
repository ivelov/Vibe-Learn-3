"use client";

import { useEffect, useRef } from "react";
import { useTradingStore } from "@/store/tradingStore";
import type { PriceUpdate } from "@/types";

/**
 * Opens an EventSource to /api/stream/prices and feeds every price update
 * into the trading store. EventSource reconnects automatically; we also
 * reflect the connection state (green/yellow/red dot in the header) and add a
 * manual reconnect fallback for browsers that give up.
 */
export function usePriceStream() {
  const esRef = useRef<EventSource | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const { updatePrice, setConnectionStatus } = useTradingStore.getState();
    let closed = false;

    function connect() {
      if (closed) return;
      setConnectionStatus("reconnecting");

      const es = new EventSource("/api/stream/prices");
      esRef.current = es;

      es.onopen = () => setConnectionStatus("connected");

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as Record<string, PriceUpdate>;
          for (const update of Object.values(data)) {
            updatePrice(update);
          }
        } catch (e) {
          console.error("Failed to parse SSE data:", e);
        }
      };

      es.onerror = () => {
        setConnectionStatus("reconnecting");
        es.close();
        esRef.current = null;
        // EventSource usually retries on its own; this is a safety net in case
        // it transitions to CLOSED permanently.
        if (!closed) {
          reconnectRef.current = setTimeout(connect, 2000);
        }
      };
    }

    connect();

    return () => {
      closed = true;
      esRef.current?.close();
      esRef.current = null;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      useTradingStore.getState().setConnectionStatus("disconnected");
    };
  }, []);
}
