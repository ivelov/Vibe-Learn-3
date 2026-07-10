import { describe, it, expect, beforeEach } from "vitest";
import {
  useTradingStore,
  selectLivePositions,
  selectLiveTotals,
} from "@/store/tradingStore";
import type { PriceUpdate, Position } from "@/types";

function makeUpdate(
  ticker: string,
  price: number,
  previous: number,
): PriceUpdate {
  return {
    ticker,
    price,
    previous_price: previous,
    change: price - previous,
    change_percent: previous ? ((price - previous) / previous) * 100 : 0,
    direction: price > previous ? "up" : price < previous ? "down" : "flat",
    timestamp: 1_700_000_000,
  };
}

beforeEach(() => {
  useTradingStore.setState({
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
  });
});

describe("updatePrice", () => {
  it("stores the latest price and accumulates history", () => {
    const { updatePrice } = useTradingStore.getState();
    updatePrice(makeUpdate("AAPL", 190, 189));
    updatePrice(makeUpdate("AAPL", 191, 190));

    const state = useTradingStore.getState();
    expect(state.prices.AAPL.price).toBe(191);
    expect(state.priceHistory.AAPL).toHaveLength(2);
    expect(state.priceHistory.AAPL.map((p) => p.price)).toEqual([190, 191]);
  });

  it("captures the first price as the session open baseline", () => {
    const { updatePrice } = useTradingStore.getState();
    updatePrice(makeUpdate("TSLA", 250, 249));
    updatePrice(makeUpdate("TSLA", 260, 250));

    expect(useTradingStore.getState().sessionOpen.TSLA).toBe(250);
  });
});

describe("watchlist actions", () => {
  it("adds and removes tickers without duplicates", () => {
    const s = useTradingStore.getState();
    s.addToWatchlistLocal("AAPL");
    s.addToWatchlistLocal("AAPL");
    expect(useTradingStore.getState().watchlist).toEqual(["AAPL"]);

    s.setSelectedTicker("AAPL");
    s.removeFromWatchlistLocal("AAPL");
    const state = useTradingStore.getState();
    expect(state.watchlist).toEqual([]);
    expect(state.selectedTicker).toBeNull();
  });
});

describe("selectLivePositions", () => {
  it("recomputes market value and P&L from live prices", () => {
    const position: Position = {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 100,
      current_price: 100,
      market_value: 1000,
      unrealized_pnl: 0,
      pnl_pct: 0,
    };
    useTradingStore.setState({ positions: [position] });
    useTradingStore.getState().updatePrice(makeUpdate("AAPL", 110, 109));

    const [live] = selectLivePositions(useTradingStore.getState());
    expect(live.current_price).toBe(110);
    expect(live.market_value).toBe(1100);
    expect(live.unrealized_pnl).toBe(100);
    expect(live.pnl_pct).toBeCloseTo(10);
  });
});

describe("selectLiveTotals", () => {
  it("sums cash and live position values", () => {
    const position: Position = {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 100,
      current_price: 100,
      market_value: 1000,
      unrealized_pnl: 0,
      pnl_pct: 0,
    };
    useTradingStore.setState({ cashBalance: 5000, positions: [position] });
    useTradingStore.getState().updatePrice(makeUpdate("AAPL", 120, 119));

    const totals = selectLiveTotals(useTradingStore.getState());
    expect(totals.totalValue).toBe(5000 + 1200);
    expect(totals.totalUnrealizedPnl).toBe(200);
  });
});
