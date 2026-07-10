import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePriceStream } from "@/hooks/usePriceStream";
import { useTradingStore } from "@/store/tradingStore";

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }
  close() {
    this.closed = true;
  }
  emitOpen() {
    this.onopen?.();
  }
  emitMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

beforeEach(() => {
  MockEventSource.instances = [];
  // @ts-expect-error - install mock
  global.EventSource = MockEventSource;
  useTradingStore.setState({
    prices: {},
    priceHistory: {},
    sessionOpen: {},
    connectionStatus: "disconnected",
  });
});

describe("usePriceStream", () => {
  it("connects and marks the connection live on open", () => {
    renderHook(() => usePriceStream());
    const es = MockEventSource.instances[0];
    expect(es.url).toBe("/api/stream/prices");
    expect(useTradingStore.getState().connectionStatus).toBe("reconnecting");

    act(() => es.emitOpen());
    expect(useTradingStore.getState().connectionStatus).toBe("connected");
  });

  it("feeds SSE price payloads into the store", () => {
    renderHook(() => usePriceStream());
    const es = MockEventSource.instances[0];

    act(() =>
      es.emitMessage({
        AAPL: {
          ticker: "AAPL",
          price: 195.5,
          previous_price: 195,
          change: 0.5,
          change_percent: 0.25,
          direction: "up",
          timestamp: 1_700_000_000,
        },
      }),
    );

    expect(useTradingStore.getState().prices.AAPL.price).toBe(195.5);
  });

  it("closes the connection and resets status on unmount", () => {
    const { unmount } = renderHook(() => usePriceStream());
    const es = MockEventSource.instances[0];
    act(() => unmount());
    expect(es.closed).toBe(true);
    expect(useTradingStore.getState().connectionStatus).toBe("disconnected");
  });
});
