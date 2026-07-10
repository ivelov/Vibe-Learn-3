"use client";

import { useEffect } from "react";
import { useTradingStore } from "@/store/tradingStore";
import { usePriceStream } from "@/hooks/usePriceStream";
import { refreshAll, refreshPortfolio } from "@/lib/refresh";
import { Header } from "@/components/Header";
import { WatchlistGrid } from "@/components/WatchlistGrid";
import { MainChart } from "@/components/MainChart";
import { PortfolioHeatmap } from "@/components/PortfolioHeatmap";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { PnlChart } from "@/components/PnlChart";
import { ChatPanel } from "@/components/ChatPanel";

export default function Page() {
  usePriceStream();

  const chatOpen = useTradingStore((s) => s.chatOpen);

  // Bootstrap: load portfolio + watchlist, then keep the portfolio/history
  // fresh on a 30s cadence (matching the backend snapshot interval).
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        await refreshAll();
      } catch (e) {
        console.error("Initial data load failed:", e);
      }
      if (cancelled) return;
      // Select a default ticker for the main chart if none chosen yet.
      const { selectedTicker, watchlist, setSelectedTicker } =
        useTradingStore.getState();
      if (!selectedTicker && watchlist.length > 0) {
        setSelectedTicker(watchlist[0]);
      }
    })();

    const interval = setInterval(() => {
      refreshPortfolio().catch(() => undefined);
    }, 30_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />

      <div className="flex-1 flex min-h-0 bg-border gap-px">
        {/* Left column: watchlist + trade bar */}
        <div className="w-[300px] shrink-0 flex flex-col min-h-0 gap-px bg-border">
          <div className="flex-1 min-h-0">
            <WatchlistGrid />
          </div>
          <div className="shrink-0">
            <TradeBar />
          </div>
        </div>

        {/* Center column: chart, heatmap+positions, P&L */}
        <main className="flex-1 min-w-0 flex flex-col min-h-0 gap-px bg-border">
          <div className="flex-[5] min-h-0">
            <MainChart />
          </div>
          <div className="flex-[4] min-h-0 flex gap-px bg-border">
            <div className="flex-1 min-w-0">
              <PortfolioHeatmap />
            </div>
            <div className="flex-1 min-w-0">
              <PositionsTable />
            </div>
          </div>
          <div className="flex-[3] min-h-0">
            <PnlChart />
          </div>
        </main>

        {/* Right sidebar: AI chat (collapsible) */}
        <div
          className={`${chatOpen ? "w-[360px]" : "w-9"} shrink-0 min-h-0 transition-[width] duration-150`}
        >
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}
