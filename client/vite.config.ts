import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { extensionLoaderPlugin } from "./vite-plugin-extensions";
import * as path from "path";

// https://vite.dev/config/
export default defineConfig({
  // Load .env from repo root (shared between server and client)
  envDir: path.resolve(__dirname, ".."),
  plugins: [react(), extensionLoaderPlugin()],
  resolve: {
    alias: {
      "@extensions": path.resolve(__dirname, "../extensions"),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        silenceDeprecations: [
          "import",
          "if-function",
          "global-builtin",
          "color-functions",
        ],
      },
    },
  },
  server: {
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:8188",
        changeOrigin: true,
        secure: false,
        ws: true,
        proxyTimeout: 60_000,
        timeout: 60_000,
        configure: (proxy) => {
          proxy.on("error", (err, req, res) => {
            console.error("[vite-proxy] error:", err.message, "url:", req.url);
            const serverResponse = res as unknown as import("http").ServerResponse;
            if (!serverResponse.headersSent) {
              serverResponse.writeHead(502, {
                "Content-Type": "application/json",
              });
              serverResponse.end(
                JSON.stringify({ error: "Proxy error", detail: err.message }),
              );
            }
          });
          proxy.on("proxyReq", (proxyReq, req) => {
            console.log("[vite-proxy] →", req.method, req.url);
          });
          proxy.on("proxyRes", (proxyRes, req) => {
            console.log(
              "[vite-proxy] ←",
              req.method,
              req.url,
              proxyRes.statusCode,
            );
          });
        },
      },
    },
  },
});
