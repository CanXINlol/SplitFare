import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["./tests/setup.ts"], exclude: ["e2e/**", "node_modules/**"] },
  resolve: { alias: { "@": fileURLToPath(new URL("./", import.meta.url)) } },
});
