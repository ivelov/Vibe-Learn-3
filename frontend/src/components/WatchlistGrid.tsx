"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { useTradingStore } from "@/store/tradingStore";
import { addToWatchlist, removeFromWatchlist } from "@/app/api";
import { fmtNumber, fmtPct } from "@/lib/format";
import { Sparkline } from "./Sparkline";

export function WatchlistGrid() {
  const watchlist = useTradingStore((s) => s.watchlist);
  const addLocal = useTradingStore((s) => s.addToWatchlistLocal);
  const removeLocal = useTradingStore((s) => s.removeFromWatchlistLocal);

  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    setBusy(true);
    setError(null);
    try {
      const res = await addToWatchlist(ticker);
      if (res.added) {
        addLocal(res.ticker);
        setInput("");
      } else {
        setError(res.reason ?? `Could not add ${ticker}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add ticker");
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(ticker: string) {
    removeLocal(ticker); // optimistic
    try {
      await removeFromWatchlist(ticker);
    } catch {
      addLocal(ticker); // rollback on failure
    }
  }

  return (
    <section className="flex flex-col h-full bg-surface">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Watchlist
        </h2>
        <form onSubmit={handleAdd} className="flex items-center gap-1">
          <input
            aria-label="Add ticker"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="ADD"
            maxLength={8}
            className="w-16 bg-bg border border-border rounded px-2 py-0.5 text-xs uppercase text-white outline-none focus:border-blue"
          />
          <button
            type="submit"
            disabled={busy}
            className="text-blue hover:text-white text-sm px-1 disabled:opacity-50"
            aria-label="Confirm add ticker"
          >
            +
          </button>
        </form>
      </div>

      {error && (
        <div className="px-3 py-1 text-[11px] text-down border-b border-border">
          {error}
        </div>
      )}

      <div className="overflow-y-auto flex-1 min-h-0">
        {watchlist.length === 0 ? (
          <div className="p-4 text-xs text-gray-500">No tickers watched.</div>
        ) : (
          <ul>
            {watchlist.map((ticker) => (
              <WatchlistCard
                key={ticker}
                ticker={ticker}
                onRemove={handleRemove}
              />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function WatchlistCard({
  ticker,
  onRemove,
}: {
  ticker: string;
  onRemove: (ticker: string) => void;
}) {
  const price = useTradingStore((s) => s.prices[ticker]?.price);
  const open = useTradingStore((s) => s.sessionOpen[ticker]);
  const series = useTradingStore((s) => s.priceHistory[ticker]);
  const selected = useTradingStore((s) => s.selectedTicker === ticker);
  const setSelected = useTradingStore((s) => s.setSelectedTicker);

  const priceRef = useRef<HTMLDivElement>(null);
  const prevPriceRef = useRef<number | null>(null);

  // Flash only the price cell (not the whole row) on each price change.
  useEffect(() => {
    if (price === undefined) return;
    const prev = prevPriceRef.current;
    prevPriceRef.current = price;
    if (prev === null || price === prev) return;
    const el = priceRef.current;
    if (!el) return;
    const cls = price > prev ? "flash-up" : "flash-down";
    el.classList.remove("flash-up", "flash-down");
    void el.offsetWidth;
    el.classList.add(cls);
  }, [price]);

  const changePct = useMemo(() => {
    if (price === undefined || open === undefined || open === 0) return 0;
    return ((price - open) / open) * 100;
  }, [price, open]);

  const sparkData = useMemo(
    () => (series ?? []).slice(-40).map((p) => p.price),
    [series],
  );

  const up = changePct > 0;
  const down = changePct < 0;
  const changeColor = up ? "text-up" : down ? "text-down" : "text-gray-400";
  const sparkColor = up ? "#2ea043" : down ? "#f85149" : "#209dd7";

  return (
    <li
      onClick={() => setSelected(ticker)}
      className={`group flex items-center gap-2 px-3 py-2 border-b border-border cursor-pointer hover:bg-white/5 ${
        selected ? "bg-white/5 border-l-2 border-l-blue" : "border-l-2 border-l-transparent"
      }`}
    >
      <div className="w-14 shrink-0">
        <div className="text-sm font-semibold text-white">{ticker}</div>
        <div className={`text-[11px] ${changeColor} tabular-nums`}>
          {up ? "▲" : down ? "▼" : "—"} {fmtPct(changePct)}
        </div>
      </div>

      <div className="flex-1 flex justify-center">
        <Sparkline data={sparkData} color={sparkColor} />
      </div>

      <div className="w-20 shrink-0 text-right">
        <div ref={priceRef} className="text-sm text-white tabular-nums rounded px-0.5">
          {price !== undefined ? fmtNumber(price) : "—"}
        </div>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove(ticker);
        }}
        aria-label={`Remove ${ticker}`}
        className="w-4 text-gray-600 hover:text-down opacity-0 group-hover:opacity-100 text-xs"
      >
        ×
      </button>
    </li>
  );
}
