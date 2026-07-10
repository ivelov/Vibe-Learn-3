"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useTradingStore } from "@/store/tradingStore";
import { useMounted } from "@/hooks/useMounted";
import { fmtNumber, fmtPct } from "@/lib/format";

export function MainChart() {
  const mounted = useMounted();
  const selected = useTradingStore((s) => s.selectedTicker);
  const series = useTradingStore((s) =>
    selected ? s.priceHistory[selected] : undefined,
  );
  const price = useTradingStore((s) =>
    selected ? s.prices[selected]?.price : undefined,
  );
  const open = useTradingStore((s) =>
    selected ? s.sessionOpen[selected] : undefined,
  );

  const data = useMemo(
    () =>
      (series ?? []).map((p) => ({
        t: p.t,
        price: p.price,
        label: new Date(p.t).toLocaleTimeString(),
      })),
    [series],
  );

  const changePct =
    price !== undefined && open !== undefined && open !== 0
      ? ((price - open) / open) * 100
      : 0;
  const lineColor =
    changePct > 0 ? "#2ea043" : changePct < 0 ? "#f85149" : "#209dd7";

  return (
    <section className="flex flex-col h-full bg-surface">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <div className="flex items-baseline gap-3">
          <h2 className="text-sm font-semibold text-white">
            {selected ?? "—"}
          </h2>
          {price !== undefined && (
            <span className="text-lg font-semibold text-white tabular-nums">
              {fmtNumber(price)}
            </span>
          )}
          {selected && (
            <span
              className={`text-xs tabular-nums ${
                changePct > 0
                  ? "text-up"
                  : changePct < 0
                    ? "text-down"
                    : "text-gray-400"
              }`}
            >
              {fmtPct(changePct)} <span className="text-gray-500">(session)</span>
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 p-2">
        {!selected ? (
          <Empty text="Select a ticker from the watchlist to view its chart." />
        ) : data.length < 2 ? (
          <Empty text="Accumulating live price data…" />
        ) : mounted ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
            >
              <CartesianGrid stroke="#21262d" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: "#8b949e", fontSize: 10 }}
                stroke="#30363d"
                minTickGap={48}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fill: "#8b949e", fontSize: 10 }}
                stroke="#30363d"
                width={56}
                tickFormatter={(v) => fmtNumber(v)}
                orientation="right"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: 6,
                  fontSize: 12,
                }}
                labelStyle={{ color: "#8b949e" }}
                formatter={(v: number) => [fmtNumber(v), "Price"]}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke={lineColor}
                strokeWidth={1.75}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : null}
      </div>
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="h-full flex items-center justify-center text-xs text-gray-500">
      {text}
    </div>
  );
}
