import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "@/components/ChatPanel";
import { useTradingStore } from "@/store/tradingStore";
import * as api from "@/app/api";

vi.mock("@/app/api", () => ({
  sendChat: vi.fn(),
}));

vi.mock("@/lib/refresh", () => ({
  refreshPortfolio: vi.fn().mockResolvedValue(undefined),
  refreshWatchlist: vi.fn().mockResolvedValue(undefined),
}));

beforeEach(() => {
  useTradingStore.setState({
    chatMessages: [],
    chatLoading: false,
    chatOpen: true,
  });
  vi.clearAllMocks();
});

describe("ChatPanel", () => {
  it("shows the empty-state prompt initially", () => {
    render(<ChatPanel />);
    expect(screen.getByText(/How is my portfolio doing/)).toBeInTheDocument();
  });

  it("sends a message and renders the assistant reply with a trade chip", async () => {
    const user = userEvent.setup();
    vi.mocked(api.sendChat).mockResolvedValue({
      message: "Bought 10 shares of NVDA for you.",
      trades: [{ ticker: "NVDA", side: "buy", quantity: 10 }],
      watchlist_changes: [],
      error: null,
    });

    render(<ChatPanel />);
    await user.type(screen.getByPlaceholderText("Ask FinAlly…"), "buy nvda");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(api.sendChat).toHaveBeenCalledWith("buy nvda");
    expect(screen.getByText("buy nvda")).toBeInTheDocument();
    expect(
      await screen.findByText("Bought 10 shares of NVDA for you."),
    ).toBeInTheDocument();
    expect(screen.getByText("BUY 10 NVDA")).toBeInTheDocument();
  });

  it("renders an error bubble when the request fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.sendChat).mockRejectedValue(new Error("500: boom"));

    render(<ChatPanel />);
    await user.type(screen.getByPlaceholderText("Ask FinAlly…"), "hello");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByText(/couldn't process that request/),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/500: boom/)).toBeInTheDocument(),
    );
  });

  it("collapses when the collapse control is clicked", async () => {
    const user = userEvent.setup();
    render(<ChatPanel />);
    await user.click(screen.getByLabelText("Collapse chat"));
    expect(useTradingStore.getState().chatOpen).toBe(false);
  });
});
