import { create } from "zustand";
import type {
  PriceUpdate,
  Position,
  Portfolio,
  ChatMessage,
  HistoryPoint,
} from "@/types";

// Max points kept per ticker for the accumulated price series (sparklines
// and the main chart). At ~500ms/tick this is ~5 minutes of history.
const MAX_HISTORY = 600;

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export interface PricePoint {
  t: number; // Unix ms
  price: number;
}

export interface TradingStore {
  // Prices
  prices: Record<string, PriceUpdate>;
  priceHistory: Record<string, PricePoint[]>; // accumulated since page load
  sessionOpen: Record<string, number>; // first price seen this session

  // Portfolio
  cashBalance: number;
  positions: Position[];
  totalValue: number;
  totalUnrealizedPnl: number;
  history: HistoryPoint[];

  // Watchlist
  watchlist: string[];
  selectedTicker: string | null;

  // Chat
  chatMessages: ChatMessage[];
  chatLoading: boolean;
  chatOpen: boolean;

  // SSE
  connectionStatus: ConnectionStatus;

  // Actions
  updatePrice: (update: PriceUpdate) => void;
  setPortfolio: (data: Portfolio) => void;
  setHistory: (history: HistoryPoint[]) => void;
  setWatchlist: (watchlist: string[]) => void;
  addToWatchlistLocal: (ticker: string) => void;
  removeFromWatchlistLocal: (ticker: string) => void;
  setSelectedTicker: (ticker: string | null) => void;
  addChatMessage: (msg: ChatMessage) => void;
  setChatLoading: (loading: boolean) => void;
  toggleChat: () => void;
  clearChat: () => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}

export const useTradingStore = create<TradingStore>((set) => ({
  prices: {},
  priceHistory: {},
  sessionOpen: {},

  cashBalance: 0,
  positions: [],
  totalValue: 0,
  totalUnrealizedPnl: 0,
  history: [],

  watchlist: [],
  selectedTicker: null,

  chatMessages: [],
  chatLoading: false,
  chatOpen: true,

  connectionStatus: "disconnected",

  updatePrice: (update) =>
    set((state) => {
      const ticker = update.ticker;
      if (!ticker || typeof update.price !== "number") return state;

      const tMs =
        typeof update.timestamp === "number"
          ? update.timestamp * 1000
          : Date.now();

      const existing = state.priceHistory[ticker] ?? [];
      const nextSeries = [...existing, { t: tMs, price: update.price }];
      if (nextSeries.length > MAX_HISTORY) {
        nextSeries.splice(0, nextSeries.length - MAX_HISTORY);
      }

      return {
        prices: { ...state.prices, [ticker]: update },
        priceHistory: { ...state.priceHistory, [ticker]: nextSeries },
        sessionOpen:
          state.sessionOpen[ticker] === undefined
            ? { ...state.sessionOpen, [ticker]: update.price }
            : state.sessionOpen,
      };
    }),

  setPortfolio: (data) =>
    set({
      cashBalance: data.cash_balance,
      positions: data.positions,
      totalValue: data.total_value,
      totalUnrealizedPnl: data.total_unrealized_pnl,
    }),

  setHistory: (history) => set({ history }),

  setWatchlist: (watchlist) => set({ watchlist }),

  addToWatchlistLocal: (ticker) =>
    set((state) =>
      state.watchlist.includes(ticker)
        ? state
        : { watchlist: [...state.watchlist, ticker] },
    ),

  removeFromWatchlistLocal: (ticker) =>
    set((state) => ({
      watchlist: state.watchlist.filter((t) => t !== ticker),
      selectedTicker:
        state.selectedTicker === ticker ? null : state.selectedTicker,
    })),

  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),

  addChatMessage: (msg) =>
    set((state) => ({ chatMessages: [...state.chatMessages, msg] })),

  setChatLoading: (loading) => set({ chatLoading: loading }),

  toggleChat: () => set((state) => ({ chatOpen: !state.chatOpen })),

  clearChat: () => set({ chatMessages: [] }),

  setConnectionStatus: (status) => set({ connectionStatus: status }),
}));

// --- Derived selectors (computed from live prices) ---

/** Positions recomputed against the latest live prices from the SSE stream. */
export function selectLivePositions(state: TradingStore): Position[] {
  return state.positions.map((p) => {
    const live = state.prices[p.ticker]?.price ?? p.current_price;
    const marketValue = live * p.quantity;
    const costBasis = p.avg_cost * p.quantity;
    const unrealized = marketValue - costBasis;
    const pnlPct = costBasis !== 0 ? (unrealized / costBasis) * 100 : 0;
    return {
      ...p,
      current_price: live,
      market_value: marketValue,
      unrealized_pnl: unrealized,
      pnl_pct: pnlPct,
    };
  });
}

/** Live total portfolio value = cash + market value of all positions. */
export function selectLiveTotals(state: TradingStore): {
  totalValue: number;
  totalUnrealizedPnl: number;
} {
  const livePositions = selectLivePositions(state);
  const positionsValue = livePositions.reduce(
    (sum, p) => sum + p.market_value,
    0,
  );
  const totalUnrealizedPnl = livePositions.reduce(
    (sum, p) => sum + p.unrealized_pnl,
    0,
  );
  return {
    totalValue: state.cashBalance + positionsValue,
    totalUnrealizedPnl,
  };
}
