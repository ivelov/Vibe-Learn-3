"use client";

import { useTradingStore, selectLiveTotals } from "@/store/tradingStore";
import { fmtMoney, fmtSignedMoney } from "@/lib/format";

const STATUS_META: Record<
  string,
  { color: string; label: string }
> = {
  connected: { color: "bg-up", label: "LIVE" },
  reconnecting: { color: "bg-accent", label: "RECONNECTING" },
  disconnected: { color: "bg-down", label: "OFFLINE" },
};

export function Header() {
  const cashBalance = useTradingStore((s) => s.cashBalance);
  const connectionStatus = useTradingStore((s) => s.connectionStatus);
  const { totalValue, totalUnrealizedPnl } = useTradingStore(selectLiveTotals);

  const status = STATUS_META[connectionStatus] ?? STATUS_META.disconnected;
  const pnlColor =
    totalUnrealizedPnl > 0
      ? "text-up"
      : totalUnrealizedPnl < 0
        ? "text-down"
        : "text-gray-400";

  return (
    <header className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface shrink-0">
      <div className="flex items-center gap-6">
        <div className="flex items-baseline gap-2">
          <h1 className="text-accent font-bold text-lg tracking-tight">
            FinAlly
          </h1>
          <span className="text-[10px] text-gray-500 uppercase tracking-widest">
            AI Trading
          </span>
        </div>

        <div className="hidden sm:flex items-center gap-6 text-sm">
          <Stat label="Portfolio">
            <span className="text-white font-semibold tabular-nums">
              {fmtMoney(totalValue)}
            </span>
          </Stat>
          <Stat label="Cash">
            <span className="text-white tabular-nums">
              {fmtMoney(cashBalance)}
            </span>
          </Stat>
          <Stat label="Unrealized P&L">
            <span className={`${pnlColor} font-semibold tabular-nums`}>
              {fmtSignedMoney(totalUnrealizedPnl)}
            </span>
          </Stat>
        </div>
      </div>

      <div className="flex items-center gap-2" title={connectionStatus}>
        <span
          className={`inline-block w-2.5 h-2.5 rounded-full ${status.color} ${
            connectionStatus === "reconnecting" ? "animate-pulse" : ""
          }`}
        />
        <span className="text-xs text-gray-400 uppercase tracking-wide">
          {status.label}
        </span>
      </div>
    </header>
  );
}

function Stat({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col leading-tight">
      <span className="text-[10px] text-gray-500 uppercase tracking-wide">
        {label}
      </span>
      {children}
    </div>
  );
}
