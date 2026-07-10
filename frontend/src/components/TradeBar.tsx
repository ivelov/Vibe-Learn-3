"use client";

import { useEffect, useState } from "react";
import { useTradingStore } from "@/store/tradingStore";
import {
  executeTrade,
  fetchPortfolio,
  fetchHistory,
} from "@/app/api";
import { fmtMoney } from "@/lib/format";

export function TradeBar() {
  const selected = useTradingStore((s) => s.selectedTicker);
  const setPortfolio = useTradingStore((s) => s.setPortfolio);
  const setHistory = useTradingStore((s) => s.setHistory);
  const addLocal = useTradingStore((s) => s.addToWatchlistLocal);

  const [ticker, setTicker] = useState("");
  const [qty, setQty] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Keep the ticker field in sync with the selected watchlist ticker.
  useEffect(() => {
    if (selected) setTicker(selected);
  }, [selected]);

  const livePrice = useTradingStore((s) =>
    ticker ? s.prices[ticker.toUpperCase()]?.price : undefined,
  );
  const quantityNum = parseFloat(qty);
  const estimate =
    livePrice !== undefined && Number.isFinite(quantityNum) && quantityNum > 0
      ? livePrice * quantityNum
      : null;

  async function refresh() {
    try {
      const [portfolio, history] = await Promise.all([
        fetchPortfolio(),
        fetchHistory(),
      ]);
      setPortfolio(portfolio);
      setHistory(history);
    } catch {
      /* non-fatal: live prices keep the UI usable */
    }
  }

  async function submit(side: "buy" | "sell") {
    setError(null);
    setNotice(null);
    const sym = ticker.trim().toUpperCase();
    const q = parseFloat(qty);
    if (!sym) {
      setError("Enter a ticker.");
      return;
    }
    if (!Number.isFinite(q) || q <= 0) {
      setError("Enter a quantity greater than 0.");
      return;
    }
    setBusy(true);
    try {
      const res = await executeTrade(sym, q, side);
      if (res.success) {
        setNotice(
          `${side === "buy" ? "Bought" : "Sold"} ${q} ${sym} @ ${
            res.trade ? fmtMoney(res.trade.price) : "market"
          }`,
        );
        setQty("");
        addLocal(sym); // ensure traded ticker is visible in the watchlist
        await refresh();
      } else {
        setError(res.error ?? "Trade failed.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trade failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="bg-surface border-t border-border">
      <div className="px-3 py-2">
        <div className="flex items-center gap-2 flex-wrap">
          <input
            aria-label="Ticker"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
            maxLength={8}
            className="w-24 bg-bg border border-border rounded px-2 py-1 text-sm uppercase text-white outline-none focus:border-blue"
          />
          <input
            aria-label="Quantity"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            placeholder="QTY"
            inputMode="decimal"
            className="w-20 bg-bg border border-border rounded px-2 py-1 text-sm text-white outline-none focus:border-blue"
          />
          <button
            onClick={() => submit("buy")}
            disabled={busy}
            className="px-4 py-1 rounded text-sm font-semibold bg-up/90 hover:bg-up text-white disabled:opacity-50"
          >
            Buy
          </button>
          <button
            onClick={() => submit("sell")}
            disabled={busy}
            className="px-4 py-1 rounded text-sm font-semibold bg-down/90 hover:bg-down text-white disabled:opacity-50"
          >
            Sell
          </button>
          <div className="text-xs text-gray-400 ml-1 tabular-nums">
            {livePrice !== undefined && (
              <span>
                @ <span className="text-white">{fmtMoney(livePrice)}</span>
              </span>
            )}
            {estimate !== null && (
              <span className="ml-2">
                ≈ <span className="text-accent">{fmtMoney(estimate)}</span>
              </span>
            )}
          </div>
        </div>
        {error && <div className="mt-1 text-[11px] text-down">{error}</div>}
        {notice && <div className="mt-1 text-[11px] text-up">{notice}</div>}
      </div>
    </section>
  );
}
