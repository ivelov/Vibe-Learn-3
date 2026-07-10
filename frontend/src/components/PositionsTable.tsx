"use client";

import { useMemo, useState } from "react";
import { useTradingStore, selectLivePositions } from "@/store/tradingStore";
import { fmtMoney, fmtNumber, fmtPct, fmtQty, fmtSignedMoney } from "@/lib/format";

type SortKey = "ticker" | "market_value" | "unrealized_pnl" | "pnl_pct";

export function PositionsTable() {
  const positions = useTradingStore(selectLivePositions);
  const setSelected = useTradingStore((s) => s.setSelectedTicker);
  const [sortKey, setSortKey] = useState<SortKey>("unrealized_pnl");
  const [asc, setAsc] = useState(false);

  const held = useMemo(
    () => positions.filter((p) => p.quantity > 0),
    [positions],
  );

  const sorted = useMemo(() => {
    const arr = [...held];
    arr.sort((a, b) => {
      let cmp: number;
      if (sortKey === "ticker") cmp = a.ticker.localeCompare(b.ticker);
      else cmp = a[sortKey] - b[sortKey];
      return asc ? cmp : -cmp;
    });
    return arr;
  }, [held, sortKey, asc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(false);
    }
  }

  return (
    <section className="flex flex-col h-full bg-surface">
      <div className="px-3 py-2 border-b border-border shrink-0">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Positions
        </h2>
      </div>
      <div className="flex-1 min-h-0 overflow-auto">
        {sorted.length === 0 ? (
          <div className="p-4 text-xs text-gray-500">No open positions.</div>
        ) : (
          <table className="w-full text-xs tabular-nums">
            <thead className="sticky top-0 bg-surface">
              <tr className="text-gray-500 text-left border-b border-border">
                <Th onClick={() => toggleSort("ticker")} active={sortKey === "ticker"} asc={asc}>
                  Ticker
                </Th>
                <Th right>Qty</Th>
                <Th right>Avg Cost</Th>
                <Th right>Price</Th>
                <Th
                  right
                  onClick={() => toggleSort("market_value")}
                  active={sortKey === "market_value"}
                  asc={asc}
                >
                  Value
                </Th>
                <Th
                  right
                  onClick={() => toggleSort("unrealized_pnl")}
                  active={sortKey === "unrealized_pnl"}
                  asc={asc}
                >
                  P&L
                </Th>
                <Th
                  right
                  onClick={() => toggleSort("pnl_pct")}
                  active={sortKey === "pnl_pct"}
                  asc={asc}
                >
                  P&L %
                </Th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((p) => {
                const pnlColor =
                  p.unrealized_pnl > 0
                    ? "text-up"
                    : p.unrealized_pnl < 0
                      ? "text-down"
                      : "text-gray-400";
                return (
                  <tr
                    key={p.ticker}
                    onClick={() => setSelected(p.ticker)}
                    className="border-b border-border/50 hover:bg-white/5 cursor-pointer"
                  >
                    <td className="px-3 py-1.5 font-semibold text-white">
                      {p.ticker}
                    </td>
                    <td className="px-3 py-1.5 text-right text-gray-300">
                      {fmtQty(p.quantity)}
                    </td>
                    <td className="px-3 py-1.5 text-right text-gray-300">
                      {fmtNumber(p.avg_cost)}
                    </td>
                    <td className="px-3 py-1.5 text-right text-white">
                      {fmtNumber(p.current_price)}
                    </td>
                    <td className="px-3 py-1.5 text-right text-white">
                      {fmtMoney(p.market_value)}
                    </td>
                    <td className={`px-3 py-1.5 text-right ${pnlColor}`}>
                      {fmtSignedMoney(p.unrealized_pnl)}
                    </td>
                    <td className={`px-3 py-1.5 text-right ${pnlColor}`}>
                      {fmtPct(p.pnl_pct)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

function Th({
  children,
  right,
  onClick,
  active,
  asc,
}: {
  children: React.ReactNode;
  right?: boolean;
  onClick?: () => void;
  active?: boolean;
  asc?: boolean;
}) {
  return (
    <th
      onClick={onClick}
      className={`px-3 py-1.5 font-medium ${right ? "text-right" : "text-left"} ${
        onClick ? "cursor-pointer hover:text-white select-none" : ""
      } ${active ? "text-white" : ""}`}
    >
      {children}
      {active ? (asc ? " ▲" : " ▼") : ""}
    </th>
  );
}
