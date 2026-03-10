import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, "../server/scheduler_app/static/app"),
    emptyOutDir: true
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/oauth": "http://localhost:8000",
      "/webhooks": "http://localhost:8000"
    }
  }
});
