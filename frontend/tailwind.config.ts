import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0d1117",
        surface: "#161b22",
        panel: "#1a1a2e",
        border: "#30363d",
        accent: "#ecad0a",
        blue: "#209dd7",
        purple: "#753991",
        up: "#2ea043",
        down: "#f85149",
      },
      fontFamily: {
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};
export default config;
