"use client";

import { useEffect, useRef, useState } from "react";
import { useTradingStore } from "@/store/tradingStore";
import { sendChat } from "@/app/api";
import { refreshPortfolio, refreshWatchlist } from "@/lib/refresh";
import type { ChatAction } from "@/types";

export function ChatPanel() {
  const messages = useTradingStore((s) => s.chatMessages);
  const loading = useTradingStore((s) => s.chatLoading);
  const open = useTradingStore((s) => s.chatOpen);
  const addMessage = useTradingStore((s) => s.addChatMessage);
  const setLoading = useTradingStore((s) => s.setChatLoading);
  const toggle = useTradingStore((s) => s.toggleChat);

  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    addMessage({ role: "user", content: text });
    setLoading(true);
    try {
      const res = await sendChat(text);
      addMessage({
        role: "assistant",
        content: res.message,
        trades: res.trades,
        watchlist_changes: res.watchlist_changes,
        error: res.error,
      });
      // The assistant may have executed trades or edited the watchlist.
      await Promise.all([refreshPortfolio(), refreshWatchlist()]).catch(
        () => undefined,
      );
    } catch (err) {
      addMessage({
        role: "assistant",
        content: "Sorry, I couldn't process that request.",
        error: err instanceof Error ? err.message : "Request failed",
      });
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={toggle}
        className="h-full w-9 bg-surface border-l border-border flex flex-col items-center justify-center gap-2 hover:bg-white/5"
        aria-label="Open AI chat"
      >
        <span className="text-purple text-lg">✦</span>
        <span
          className="text-[10px] text-gray-400 uppercase tracking-widest"
          style={{ writingMode: "vertical-rl" }}
        >
          AI Chat
        </span>
      </button>
    );
  }

  return (
    <aside className="h-full w-full flex flex-col bg-surface border-l border-border">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-purple">✦</span>
          <h2 className="text-sm font-semibold text-white">FinAlly Copilot</h2>
        </div>
        <button
          onClick={toggle}
          className="text-gray-500 hover:text-white text-sm"
          aria-label="Collapse chat"
        >
          ⟩
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-xs text-gray-500 leading-relaxed">
            Ask me to analyze your portfolio, suggest trades, or manage your
            watchlist. For example:
            <ul className="mt-2 space-y-1 text-gray-400">
              <li>· “How is my portfolio doing?”</li>
              <li>· “Buy 10 shares of NVDA.”</li>
              <li>· “Add PYPL to my watchlist.”</li>
            </ul>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span className="spinner inline-block w-3 h-3 border-2 border-gray-600 border-t-blue rounded-full" />
            FinAlly is thinking…
          </div>
        )}
      </div>

      <form
        onSubmit={handleSend}
        className="p-2 border-t border-border shrink-0 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask FinAlly…"
          disabled={loading}
          className="flex-1 bg-bg border border-border rounded px-3 py-2 text-sm text-white outline-none focus:border-purple disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-2 rounded text-sm font-semibold bg-purple hover:bg-purple/80 text-white disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </aside>
  );
}

function MessageBubble({
  message,
}: {
  message: {
    role: "user" | "assistant";
    content: string;
    trades?: ChatAction[];
    watchlist_changes?: ChatAction[];
    error?: string | null;
  };
}) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
          isUser
            ? "bg-blue/20 text-white"
            : "bg-bg border border-border text-gray-200"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{message.content}</p>

        {message.trades && message.trades.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.trades.map((t, i) => (
              <ActionChip key={i} action={t} kind="trade" />
            ))}
          </div>
        )}

        {message.watchlist_changes && message.watchlist_changes.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.watchlist_changes.map((c, i) => (
              <ActionChip key={i} action={c} kind="watchlist" />
            ))}
          </div>
        )}

        {message.error && (
          <div className="mt-2 text-[11px] text-down">⚠ {message.error}</div>
        )}
      </div>
    </div>
  );
}

function ActionChip({
  action,
  kind,
}: {
  action: ChatAction;
  kind: "trade" | "watchlist";
}) {
  const failed = action.success === false || !!action.error;
  const label =
    kind === "trade"
      ? `${action.side?.toUpperCase() ?? ""} ${action.quantity ?? ""} ${action.ticker}`
      : `${action.action === "remove" ? "Remove" : "Add"} ${action.ticker}`;

  return (
    <div
      className={`flex items-center gap-1.5 text-[11px] rounded px-2 py-1 ${
        failed
          ? "bg-down/15 text-down"
          : "bg-up/15 text-up"
      }`}
    >
      <span>{failed ? "✕" : "✓"}</span>
      <span className="text-gray-200">{label.trim()}</span>
      {failed && <span className="text-down">— {action.error}</span>}
    </div>
  );
}
