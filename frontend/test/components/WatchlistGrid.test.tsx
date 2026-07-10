import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WatchlistGrid } from "@/components/WatchlistGrid";
import { useTradingStore } from "@/store/tradingStore";
import * as api from "@/app/api";

vi.mock("@/app/api", () => ({
  addToWatchlist: vi.fn(),
  removeFromWatchlist: vi.fn(),
}));

function seedPrice(ticker: string, price: number) {
  useTradingStore.getState().updatePrice({
    ticker,
    price,
    previous_price: price - 1,
    change: 1,
    change_percent: 0.5,
    direction: "up",
    timestamp: 1_700_000_000,
  });
}

beforeEach(() => {
  useTradingStore.setState({
    prices: {},
    priceHistory: {},
    sessionOpen: {},
    watchlist: [],
    selectedTicker: null,
  });
  vi.clearAllMocks();
});

describe("WatchlistGrid", () => {
  it("renders watched tickers with prices", () => {
    useTradingStore.setState({ watchlist: ["AAPL"] });
    seedPrice("AAPL", 190.25);
    render(<WatchlistGrid />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("190.25")).toBeInTheDocument();
  });

  it("selects a ticker on click", async () => {
    const user = userEvent.setup();
    useTradingStore.setState({ watchlist: ["AAPL"] });
    seedPrice("AAPL", 190);
    render(<WatchlistGrid />);
    await user.click(screen.getByText("AAPL"));
    expect(useTradingStore.getState().selectedTicker).toBe("AAPL");
  });

  it("adds a ticker via the input", async () => {
    const user = userEvent.setup();
    vi.mocked(api.addToWatchlist).mockResolvedValue({
      ticker: "NVDA",
      added: true,
    });
    render(<WatchlistGrid />);

    await user.type(screen.getByLabelText("Add ticker"), "nvda");
    await user.click(screen.getByLabelText("Confirm add ticker"));

    await waitFor(() =>
      expect(useTradingStore.getState().watchlist).toContain("NVDA"),
    );
    expect(api.addToWatchlist).toHaveBeenCalledWith("NVDA");
  });

  it("shows an error when a ticker cannot be added", async () => {
    const user = userEvent.setup();
    vi.mocked(api.addToWatchlist).mockResolvedValue({
      ticker: "ZZZZ",
      added: false,
      reason: "Unknown ticker",
    });
    render(<WatchlistGrid />);

    await user.type(screen.getByLabelText("Add ticker"), "zzzz");
    await user.click(screen.getByLabelText("Confirm add ticker"));

    expect(await screen.findByText("Unknown ticker")).toBeInTheDocument();
  });

  it("removes a ticker optimistically", async () => {
    const user = userEvent.setup();
    vi.mocked(api.removeFromWatchlist).mockResolvedValue({
      ticker: "AAPL",
      removed: true,
    });
    useTradingStore.setState({ watchlist: ["AAPL"] });
    seedPrice("AAPL", 190);
    render(<WatchlistGrid />);

    await user.click(screen.getByLabelText("Remove AAPL"));
    expect(useTradingStore.getState().watchlist).not.toContain("AAPL");
  });
});
