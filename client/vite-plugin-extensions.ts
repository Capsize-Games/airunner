/**
 * Vite plugin that generates a `virtual:extensions` module at build time.
 *
 * The plugin reads the `AIRUNNER_EXTENSIONS` environment variable (from .env)
 * to discover which extensions are active. If empty, it auto-scans the
 * `extensions/` directory for any subdirectories containing a `config.py`.
 *
 * For each active extension, it checks the convention-based client directory
 * and generates appropriate imports for route elements and providers.
 */

import type { Plugin } from "vite";
import * as fs from "fs";
import * as path from "path";

const VIRTUAL_MODULE_ID = "virtual:extensions";
const RESOLVED_VIRTUAL_MODULE_ID = "\0" + VIRTUAL_MODULE_ID;

/** Root directory where extensions live. */
const EXTENSIONS_DIR = path.resolve(__dirname, "../extensions");

/**
 * Parse the AIRUNNER_EXTENSIONS setting into a list of extension names.
 */
function parseExtensionNames(): string[] {
  const raw = process.env.AIRUNNER_EXTENSIONS || "";
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) =>
      s.replace(/^extensions\./, "").replace(/\.config$/, ""),
    );
}

/**
 * Auto-discover extensions by scanning the extensions/ directory.
 * Returns names of subdirectories that contain a config.py file.
 */
function autodiscoverExtensions(): string[] {
  const names: string[] = [];
  try {
    if (!fs.existsSync(EXTENSIONS_DIR)) return names;
    for (const entry of fs.readdirSync(EXTENSIONS_DIR)) {
      const entryPath = path.join(EXTENSIONS_DIR, entry);
      if (!fs.statSync(entryPath).isDirectory()) continue;
      const configPath = path.join(entryPath, "config.py");
      if (fs.existsSync(configPath)) {
        names.push(entry);
      }
    }
  } catch {
    // extensions/ dir doesn't exist — normal in core
  }
  return names;
}

export function extensionLoaderPlugin(): Plugin {
  return {
    name: "airunner-extension-loader",

    resolveId(id) {
      if (id === VIRTUAL_MODULE_ID) return RESOLVED_VIRTUAL_MODULE_ID;
      return null;
    },

    load(id) {
      if (id !== RESOLVED_VIRTUAL_MODULE_ID) return null;

      // Try AIRUNNER_EXTENSIONS first, fall back to auto-scan
      let extNames = parseExtensionNames();
      if (extNames.length === 0) {
        extNames = autodiscoverExtensions();
      }

      console.log("[airunner-extensions] loading:", extNames);

      const imports: string[] = [];
      const routeElements: string[] = [];
      const providers: string[] = [];
      const headerGetters: string[] = [];

      extNames.forEach((name, i) => {
        const clientDir = path.join(EXTENSIONS_DIR, name, "client");

        if (!fs.existsSync(clientDir)) return;

        const routesPath = path.join(clientDir, "routes.tsx");
        if (fs.existsSync(routesPath)) {
          imports.push(
            `import { extensionRouteElements as ext${i}RouteElements } from "@extensions/${name}/client/routes";`,
          );
          routeElements.push(`...ext${i}RouteElements`);
        }

        const providerPath = path.join(clientDir, "Provider.tsx");
        if (fs.existsSync(providerPath)) {
          imports.push(
            `import { Provider as Ext${i}Provider } from "@extensions/${name}/client/Provider";`,
          );
          providers.push(`Ext${i}Provider`);
        }

        const bottomBarPath = path.join(clientDir, "BottomBar.tsx");
        if (fs.existsSync(bottomBarPath)) {
          imports.push(
            `import { BottomBar as Ext${i}BottomBar } from "@extensions/${name}/client/BottomBar";`,
          );
        }

        const headersPath = path.join(clientDir, "headers.ts");
        if (fs.existsSync(headersPath)) {
          imports.push(
            `import { getRequestHeaders as ext${i}GetRequestHeaders } from "@extensions/${name}/client/headers";`,
          );
          headerGetters.push(`ext${i}GetRequestHeaders`);
        }
      });

      const bottomBarName =
        extNames.length > 0
          ? extNames
              .map(
                (_, i) =>
                  `Ext${i}BottomBar !== undefined ? /* @__PURE__ */React.createElement(Ext${i}BottomBar) : null`,
              )
              .filter(Boolean)
              .join("")
          : "null";

      const headerGetterBody =
        headerGetters.length > 0
          ? headerGetters
              .map((fn) => `Object.assign(h, ${fn}())`)
              .join("; ")
          : "";
      const getRequestHeadersFn = headerGetterBody
        ? `export function getRequestHeaders() { const h: Record<string, string> = {}; ${headerGetterBody}; return h; }`
        : `export function getRequestHeaders() { return {}; }`;

      const source = [
        'import { Route } from "react-router-dom";',
        'import React from "react";',
        "",
        imports.join("\n"),
        "",
        `export const extensionRouteElements = [${routeElements.join(", ")}];`,
        `export const extensionProviders = [${providers.join(", ")}];`,
        `export const extensionBottomBarItems = ${bottomBarName};`,
        getRequestHeadersFn,
      ].join("\n");

      return source;
    },
  };
}
