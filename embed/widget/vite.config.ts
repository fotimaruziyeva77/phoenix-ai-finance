import preact from "@preact/preset-vite";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [preact()],
  build: {
    lib: {
      entry: resolve(__dirname, "src/main.tsx"),
      /* Global assigned by Rollup; must match window.BotforgeWidget in main.tsx */
      name: "BotforgeWidget",
      formats: ["iife"],
      fileName: () => "botforge-widget.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        extend: true,
        exports: "named",
      },
    },
    sourcemap: true,
    target: "es2020",
  },
});
