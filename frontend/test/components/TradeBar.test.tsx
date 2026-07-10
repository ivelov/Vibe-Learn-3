import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeBar } from "@/components/TradeBar";
import { useTradingStore } from "@/store/tradingStore";
import * as api from "@/app/api";

vi.mock("@/app/api", () => ({
  executeTrade: vi.fn(),
  fetchPortfolio: vi.fn(),
  fetchHistory: vi.fn(),
}));

function seedPrice(ticker: string, price: number) {
  useTradingStore.getState().updatePrice({
    ticker,
    price,
    previous_price: price,
    change: 0,
    change_percent: 0,
    direction: "flat",
    timestamp: 1_700_000_000,
  });
}

beforeEach(() => {
  useTradingStore.setState({
    prices: {},
    priceHistory: {},
    sessionOpen: {},
    positions: [],
    watchlist: [],
    selectedTicker: null,
    cashBalance: 10000,
  });
  vi.clearAllMocks();
  vi.mocked(api.fetchPortfolio).mockResolvedValue({
    cash_balance: 8000,
    positions: [],
    total_value: 10000,
    total_unrealized_pnl: 0,
  });
  vi.mocked(api.fetchHistory).mockResolvedValue([]);
});

describe("TradeBar", () => {
  it("prefills the ticker from the selected ticker", () => {
    useTradingStore.setState({ selectedTicker: "AAPL" });
    render(<TradeBar />);
    expect(screen.getByLabelText<HTMLInputElement>("Ticker").value).toBe(
      "AAPL",
    );
  });

  it("shows an estimated cost from live price and quantity", async () => {
    const user = userEvent.setup();
    useTradingStore.setState({ selectedTicker: "AAPL" });
    seedPrice("AAPL", 200);
    render(<TradeBar />);
    await user.type(screen.getByLabelText("Quantity"), "5");
    // 200 * 5 = 1000
    expect(screen.getByText(/\$1,000\.00/)).toBeInTheDocument();
  });

  it("executes a buy trade and shows a confirmation", async () => {
    const user = userEvent.setup();
    useTradingStore.setState({ selectedTicker: "AAPL" });
    seedPrice("AAPL", 200);
    vi.mocked(api.executeTrade).mockResolvedValue({
      success: true,
      trade: {
        ticker: "AAPL",
        side: "buy",
        quantity: 5,
        price: 200,
      },
      cash_balance: 9000,
    });

    render(<TradeBar />);
    await user.type(screen.getByLabelText("Quantity"), "5");
    await user.click(screen.getByRole("button", { name: "Buy" }));

    expect(api.executeTrade).toHaveBeenCalledWith("AAPL", 5, "buy");
    expect(await screen.findByText(/Bought 5 AAPL/)).toBeInTheDocument();
    await waitFor(() => expect(api.fetchPortfolio).toHaveBeenCalled());
  });

  it("surfaces a trade error inline", async () => {
    const user = userEvent.setup();
    useTradingStore.setState({ selectedTicker: "AAPL" });
    seedPrice("AAPL", 200);
    vi.mocked(api.executeTrade).mockResolvedValue({
      success: false,
      error: "Insufficient cash",
    });

    render(<TradeBar />);
    await user.type(screen.getByLabelText("Quantity"), "500");
    await user.click(screen.getByRole("button", { name: "Buy" }));

    expect(await screen.findByText("Insufficient cash")).toBeInTheDocument();
  });

  it("validates quantity before calling the API", async () => {
    const user = userEvent.setup();
    useTradingStore.setState({ selectedTicker: "AAPL" });
    seedPrice("AAPL", 200);
    render(<TradeBar />);
    await user.click(screen.getByRole("button", { name: "Buy" }));
    expect(api.executeTrade).not.toHaveBeenCalled();
    expect(
      screen.getByText("Enter a quantity greater than 0."),
    ).toBeInTheDocument();
  });
});
