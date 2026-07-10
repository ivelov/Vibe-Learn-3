"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useTradingStore, selectLiveTotals } from "@/store/tradingStore";
import { useMounted } from "@/hooks/useMounted";
import { fmtMoney } from "@/lib/format";

export function PnlChart() {
  const mounted = useMounted();
  const history = useTradingStore((s) => s.history);
  const { totalValue } = useTradingStore(selectLiveTotals);

  const data = useMemo(() => {
    const points = history.map((h) => ({
      t: new Date(h.recorded_at).getTime(),
      value: h.total_value,
      label: new Date(h.recorded_at).toLocaleTimeString(),
    }));
    // Append the current live total as the latest point.
    if (totalValue > 0) {
      points.push({
        t: Date.now(),
        value: totalValue,
        label: "now",
      });
    }
    return points;
  }, [history, totalValue]);

  const first = data[0]?.value;
  const last = data[data.length - 1]?.value;
  const gain = first !== undefined && last !== undefined ? last - first : 0;
  const color = gain >= 0 ? "#2ea043" : "#f85149";

  return (
    <section className="flex flex-col h-full bg-surface">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Portfolio Value
        </h2>
        {last !== undefined && (
          <span className="text-xs text-white tabular-nums">
            {fmtMoney(last)}
          </span>
        )}
      </div>
      <div className="flex-1 min-h-0 p-2">
        {data.length < 2 ? (
          <div className="h-full flex items-center justify-center text-xs text-gray-500">
            Recording portfolio value…
          </div>
        ) : mounted ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
            >
              <defs>
                <linearGradient id="pnlFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
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
                width={64}
                tickFormatter={(v) => fmtMoney(v, 0)}
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
                formatter={(v: number) => [fmtMoney(v), "Value"]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={1.75}
                fill="url(#pnlFill)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : null}
      </div>
    </section>
  );
}
