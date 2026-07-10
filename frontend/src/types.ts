// Shared type definitions matching the FastAPI backend contracts.

export type Direction = "up" | "down" | "flat";

// SSE price payload (backend PriceUpdate.to_dict()).
// NOTE: `timestamp` is Unix seconds (float), not an ISO string.
export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  change: number;
  change_percent: number;
  direction: Direction;
  timestamp: number;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_pct: number;
}

export interface Portfolio {
  cash_balance: number;
  positions: Position[];
  total_value: number;
  total_unrealized_pnl: number;
}

export interface Trade {
  id?: string;
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  executed_at?: string;
}

export interface TradeResponse {
  success: boolean;
  trade?: Trade;
  cash_balance?: number;
  error?: string | null;
}

export interface HistoryPoint {
  total_value: number;
  recorded_at: string;
}

export interface WatchlistItem {
  ticker: string;
  price: number | null;
  change: number;
  change_percent: number;
  direction: Direction;
}

export interface WatchlistAddResponse {
  ticker: string;
  added: boolean;
  reason?: string | null;
}

export interface WatchlistRemoveResponse {
  ticker: string;
  removed: boolean;
}

export interface ChatAction {
  ticker: string;
  side?: "buy" | "sell";
  quantity?: number;
  action?: "add" | "remove";
  success?: boolean;
  error?: string | null;
}

export interface ChatResponse {
  message: string;
  trades: ChatAction[];
  watchlist_changes: ChatAction[];
  error?: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  trades?: ChatAction[];
  watchlist_changes?: ChatAction[];
  error?: string | null;
}

export interface Health {
  status: string;
  db_available: boolean;
  llm_available: boolean;
}
