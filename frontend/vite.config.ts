import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // dev convenience: talk to the local FastAPI backend without CORS setup
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
