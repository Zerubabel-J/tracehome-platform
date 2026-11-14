import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run build` writes plain static files to dist/. On AWS they go to the web bucket behind
// CloudFront (decision 72). For `npm run dev`, /api and /photos are forwarded to the local edge
// container, the same way CloudFront forwards them by path.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8080",
      "/photos": "http://localhost:8080",
    },
  },
});
