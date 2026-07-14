import { defineConfig } from "vite";

/** Standard Vite app: build → web/dist; CI packs dist into the wheel as web_static */
export default defineConfig({
  root: ".",
  base: "/",
  publicDir: "public",
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/runs": "http://127.0.0.1:8765",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: true,
    assetsDir: "assets",
  },
});
