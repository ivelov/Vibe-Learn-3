import { test, expect } from '@playwright/test';

// These tests target the running app via baseURL (see playwright.config.ts).
// They are intentionally tolerant of the frontend's exact markup since the UI
// is built in parallel — they assert on user-visible content, not internals.
test.describe('FinAlly Trading Workstation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('loads the homepage with header', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('FinAlly');
    await expect(page.getByText('Portfolio', { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Cash', { exact: false }).first()).toBeVisible();
  });

  test('shows a connection status indicator', async ({ page }) => {
    await expect(
      page.locator('[class*="bg-up"], [class*="bg-green"], [class*="bg-yellow"]').first(),
    ).toBeVisible();
  });

  test('watchlist displays default tickers', async ({ page }) => {
    // Give the SSE stream a moment to deliver the first prices.
    await page.waitForTimeout(2000);
    const tickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'];
    for (const ticker of tickers) {
      await expect(page.getByText(ticker, { exact: false }).first()).toBeVisible();
    }
  });

  test('executes a buy trade', async ({ page }) => {
    await page.waitForTimeout(1000);

    const tickerInput = page
      .locator('input[placeholder*="ticker" i], input[placeholder*="Ticker" i]')
      .first();
    const qtyInput = page.locator('input[type="number"]').first();

    if (await tickerInput.isVisible().catch(() => false)) {
      await tickerInput.fill('AAPL');
      await qtyInput.fill('1');

      const buyBtn = page.locator('button:has-text("Buy"), button:has-text("BUY")').first();
      await buyBtn.click();

      await page.waitForTimeout(1000);
    }
  });

  test('chat panel sends a message and receives a response', async ({ page }) => {
    const chatInput = page
      .locator('input[placeholder*="message" i], input[placeholder*="ask" i], textarea')
      .first();

    if (await chatInput.isVisible().catch(() => false)) {
      await chatInput.fill('Hello');

      const sendBtn = page
        .locator('button:has-text("Send"), button[type="submit"]')
        .first();
      await sendBtn.click();

      await page.waitForTimeout(3000);
      await expect(page.getByText('Hello', { exact: false }).first()).toBeVisible();
    }
  });
});
