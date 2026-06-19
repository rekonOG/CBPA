import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config keeps the project fast and compatible with modern Node versions.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
});
