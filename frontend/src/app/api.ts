// API helper functions. All requests are same-origin (`/api/*`).
// In production the static export is served by FastAPI on the same origin;
// during `next dev` the requests are proxied via next.config.js rewrites.

import type {
  Portfolio,
  TradeResponse,
  HistoryPoint,
  WatchlistItem,
  WatchlistAddResponse,
  WatchlistRemoveResponse,
  ChatResponse,
  Health,
} from "@/types";

const API_BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body.error ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export function fetchPortfolio(): Promise<Portfolio> {
  return request<Portfolio>("/api/portfolio");
}

export function executeTrade(
  ticker: string,
  quantity: number,
  side: "buy" | "sell",
): Promise<TradeResponse> {
  return request<TradeResponse>("/api/portfolio/trade", {
    method: "POST",
    body: JSON.stringify({ ticker, quantity, side }),
  });
}

export function fetchHistory(): Promise<HistoryPoint[]> {
  return request<HistoryPoint[]>("/api/portfolio/history");
}

export function fetchWatchlist(): Promise<WatchlistItem[]> {
  return request<WatchlistItem[]>("/api/watchlist");
}

export function addToWatchlist(ticker: string): Promise<WatchlistAddResponse> {
  return request<WatchlistAddResponse>("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export function removeFromWatchlist(
  ticker: string,
): Promise<WatchlistRemoveResponse> {
  return request<WatchlistRemoveResponse>(
    `/api/watchlist/${encodeURIComponent(ticker)}`,
    { method: "DELETE" },
  );
}

export function sendChat(message: string): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function fetchHealth(): Promise<Health> {
  return request<Health>("/api/health");
}
