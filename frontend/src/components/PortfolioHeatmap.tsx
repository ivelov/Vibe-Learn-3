"use client";

import { useMemo, useState } from "react";
import { Treemap, ResponsiveContainer } from "recharts";
import { useTradingStore, selectLivePositions } from "@/store/tradingStore";
import { useMounted } from "@/hooks/useMounted";
import { fmtMoney, fmtPct } from "@/lib/format";

interface Node {
  name: string;
  size: number;
  pnlPct: number;
  pnl: number;
}

/** Map a P&L % to a fill color: green profit, red loss, intensity by magnitude. */
function pnlColor(pnlPct: number): string {
  const magnitude = Math.min(Math.abs(pnlPct) / 8, 1); // saturate at ±8%
  const alpha = 0.25 + magnitude * 0.6;
  if (pnlPct > 0.001) return `rgba(46, 160, 67, ${alpha.toFixed(2)})`;
  if (pnlPct < -0.001) return `rgba(248, 81, 73, ${alpha.toFixed(2)})`;
  return "rgba(139, 148, 158, 0.3)";
}

interface HoverState {
  node: Node;
  x: number;
  y: number;
}

export function PortfolioHeatmap() {
  const mounted = useMounted();
  const positions = useTradingStore(selectLivePositions);
  const [hover, setHover] = useState<HoverState | null>(null);

  const data: Node[] = useMemo(
    () =>
      positions
        .filter((p) => p.quantity > 0)
        .map((p) => ({
          name: p.ticker,
          size: Math.max(p.market_value, 0.01),
          pnlPct: p.pnl_pct,
          pnl: p.unrealized_pnl,
        })),
    [positions],
  );

  return (
    <section className="flex flex-col h-full bg-surface">
      <div className="px-3 py-2 border-b border-border shrink-0">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Portfolio Heatmap
        </h2>
      </div>
      <div className="relative flex-1 min-h-0 p-1">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-gray-500">
            No positions yet. Buy shares to see your heatmap.
          </div>
        ) : mounted ? (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              stroke="#0d1117"
              isAnimationActive={false}
              content={<HeatCell onHover={setHover} />}
            />
          </ResponsiveContainer>
        ) : null}
        {hover && (
          <div
            className="pointer-events-none fixed z-50 rounded border border-border bg-surface px-2 py-1 text-xs text-white shadow-lg"
            style={{ left: hover.x + 12, top: hover.y + 12 }}
          >
            <div className="font-semibold">{hover.node.name}</div>
            <div className="text-gray-300">
              {fmtMoney(hover.node.size)} · {fmtPct(hover.node.pnlPct)}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

// Recharts spreads node props (x, y, width, height, name, plus data fields).
interface CellProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPct?: number;
  size?: number;
  pnl?: number;
  onHover?: (hover: HoverState | null) => void;
}

function HeatCell(props: CellProps) {
  const {
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    name = "",
    pnlPct = 0,
    size = 0,
    pnl = 0,
    onHover,
  } = props;
  if (width <= 0 || height <= 0) return null;
  const showLabel = width > 40 && height > 24;
  const node: Node = { name, size, pnlPct, pnl };
  return (
    <g
      onMouseEnter={(e) =>
        onHover?.({ node, x: e.clientX, y: e.clientY })
      }
      onMouseMove={(e) =>
        onHover?.({ node, x: e.clientX, y: e.clientY })
      }
      onMouseLeave={() => onHover?.(null)}
    >
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={pnlColor(pnlPct)}
        stroke="#0d1117"
        strokeWidth={2}
      />
      {showLabel && (
        <>
          <text
            x={x + 6}
            y={y + 16}
            fill="#e6edf3"
            fontSize={12}
            fontWeight={600}
          >
            {name}
          </text>
          {height > 40 && (
            <text x={x + 6} y={y + 30} fill="#c9d1d9" fontSize={10}>
              {fmtPct(pnlPct)}
            </text>
          )}
        </>
      )}
    </g>
  );
}
