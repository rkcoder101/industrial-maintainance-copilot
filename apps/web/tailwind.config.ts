import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18202a",
        panel: "#f7f8fb",
        line: "#d8dee8",
        signal: "#0f766e",
        warning: "#b45309"
      }
    }
  },
  plugins: []
};

export default config;
