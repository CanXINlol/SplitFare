import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#102a2e",
        mint: "#d8f3e8",
        coral: "#ef765f",
        paper: "#f7f5ee"
      },
      boxShadow: { card: "0 18px 50px rgba(16, 42, 46, 0.09)" }
    }
  },
  plugins: []
} satisfies Config;
