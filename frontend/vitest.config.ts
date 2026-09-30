import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  // tsconfig uses jsx:"preserve" (Next compiles it); tests need the automatic
  // React runtime so components render without importing React explicitly.
  esbuild: { jsx: "automatic" },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // Playwright specs live in /e2e and are run by Playwright, not Vitest.
    include: ["src/**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
