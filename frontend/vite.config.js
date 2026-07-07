import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API + live websocket are proxied to the FastAPI backend on :8000
export default defineConfig({
  plugins: [react()],
  // build into backend/static so the deployed backend (root dir = backend)
  // can serve the SPA itself
  build: {
    outDir: "../backend/static",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/live": { target: "ws://localhost:8000", ws: true },
    },
  },
});
