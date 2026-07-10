import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinAlly — AI Trading Workstation",
  description:
    "AI-powered trading workstation with live market data and an LLM copilot.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-bg text-[#e6edf3] font-mono antialiased">
        {children}
      </body>
    </html>
  );
}
