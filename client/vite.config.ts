import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { extensionLoaderPlugin } from "./vite-plugin-extensions";
import * as path from "path";

// https://vite.dev/config/
export default defineConfig({
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
    fs: {
      allow: [".."],
    },
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
            console.error(
              "[vite-proxy] error:",
              err.message,
              "url:",
              req.url,
            );
            if (res && "writeHead" in res) {
              try {
                const sr = res as import("http").ServerResponse;
                if (!sr.headersSent) {
                  sr.writeHead(502, {
                    "Content-Type": "application/json",
                  });
                  sr.end(
                    JSON.stringify({
                      error: "Proxy error",
                      detail: err.message,
                    }),
                  );
                }
              } catch {
                // Connection closed
              }
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
