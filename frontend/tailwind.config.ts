import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0f172a",
        foreground: "#e2e8f0",
        card: "#1e293b",
        "card-foreground": "#e2e8f0",
        primary: "#fbbf24",
        "primary-foreground": "#0f172a",
        secondary: "#334155",
        "secondary-foreground": "#e2e8f0",
        muted: "#475569",
        "muted-foreground": "#94a3b8",
        accent: "#fbbf24",
        "accent-foreground": "#0f172a",
        destructive: "#ef4444",
        "destructive-foreground": "#e2e8f0",
        border: "#334155",
        input: "#1e293b",
        ring: "#fbbf24",
      },
      fontFamily: {
        serif: ["Playfair Display", "ui-serif", "serif"],
        sans: ["Poppins", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
