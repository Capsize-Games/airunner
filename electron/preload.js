/**
 * AI Runner – Electron preload script.
 *
 * Exposes a minimal, safe API to the renderer process via contextBridge.
 * The renderer loads the React frontend directly from the Python backend,
 * so this preload is intentionally minimal.
 */

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("airunner", {
  /** Platform identifier: "linux" or "win32". */
  platform: process.platform,
  /** App version from package.json. */
  version: "6.0.0",
});
