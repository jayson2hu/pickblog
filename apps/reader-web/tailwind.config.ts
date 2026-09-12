import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#15151a",
        muted: "#5a6270",
        line: "#dfe3ea",
        panel: "#f7f8fa",
        accent: "#0f766e"
      }
    }
  },
  plugins: []
};

export default config;

