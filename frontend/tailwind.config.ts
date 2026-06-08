import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#14181c",
        foreground: "#e8e8e8",
        card: "#1c2228",
        "card-foreground": "#e8e8e8",
        primary: "#00c853",
        "primary-foreground": "#14181c",
        muted: "#2c3440",
        "muted-foreground": "#9ab",
        accent: "#00e054",
        border: "#2c3440",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
