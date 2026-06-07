/**
 * Vite plugin that generates a `virtual:extensions` module at build time.
 *
 * The plugin reads the `AIRUNNER_EXTENSIONS` environment variable (from .env)
 * to discover which extensions are active. For each active extension, it
 * checks the convention-based client directory and generates the appropriate
 * imports for route elements and providers.
 *
 * In the core repo (where AIRUNNER_EXTENSIONS is empty), the virtual module
 * exports empty arrays — no extensions are rendered.
 *
 * In the fork (where AIRUNNER_EXTENSIONS is populated), the virtual module
 * imports the extension's client code directly.
 *
 * Usage (App.tsx — same in core and fork):
 *   import { extensionRouteElements, extensionProviders } from "virtual:extensions";
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
 *
 * Input:  "extensions.auth.config,extensions.billing.config"
 * Output: ["auth", "billing"]
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

export function extensionLoaderPlugin(): Plugin {
  return {
    name: "airunner-extension-loader",

    resolveId(id) {
      if (id === VIRTUAL_MODULE_ID) return RESOLVED_VIRTUAL_MODULE_ID;
      return null;
    },

    load(id) {
      if (id !== RESOLVED_VIRTUAL_MODULE_ID) return null;

      const extNames = parseExtensionNames();
      const imports: string[] = [];
      const routeElements: string[] = [];
      const providers: string[] = [];

      extNames.forEach((name, i) => {
        const clientDir = path.join(EXTENSIONS_DIR, name, "client");

        if (!fs.existsSync(clientDir)) return;

        // Check for client route elements (JSX <Route> elements)
        const routesPath = path.join(clientDir, "routes.tsx");
        if (fs.existsSync(routesPath)) {
          imports.push(
            `import { extensionRouteElements as ext${i}RouteElements } from "@extensions/${name}/client/routes";`,
          );
          routeElements.push(`...ext${i}RouteElements`);
        }

        // Check for client Provider
        const providerPath = path.join(clientDir, "Provider.tsx");
        if (fs.existsSync(providerPath)) {
          imports.push(
            `import { Provider as Ext${i}Provider } from "@extensions/${name}/client/Provider";`,
          );
          providers.push(`Ext${i}Provider`);
        }
      });

      // Generate the virtual module source
      const source = [
        'import { Route } from "react-router-dom";',
        "",
        imports.join("\n"),
        "",
        `export const extensionRouteElements = [${routeElements.join(", ")}];`,
        `export const extensionProviders = [${providers.join(", ")}];`,
      ].join("\n");

      return source;
    },
  };
}
