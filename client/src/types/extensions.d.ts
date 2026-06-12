/**
 * Type declarations for the `virtual:extensions` Vite virtual module.
 *
 * The actual content of this module is generated at build time by the
 * `vite-plugin-extensions.ts` plugin based on the `AIRUNNER_EXTENSIONS`
 * environment variable.
 *
 * In core (empty):  exports empty arrays
 * In fork (populated): exports routes and providers from enabled extensions
 */
declare module "virtual:extensions" {
  import type { FC, ReactNode } from "react";

  /**
   * JSX elements to render as children of the root `<Routes>`.
   * Extensions export `<Route>` JSX elements directly so TypeScript
   * can resolve the discriminated union correctly.
   */
  export const extensionRouteElements: ReactNode[];

  /** Provider components registered by enabled extensions. */
  export const extensionProviders: FC<{ children: ReactNode }>[];

  /**
   * ReactNode(s) rendered at the bottom of the left icon bar.
   */
  export const extensionBottomBarItems: ReactNode;

  /**
   * Returns extra HTTP headers that extensions want added to outgoing
   * requests (e.g. Authorization from the auth extension).
   * Returns an empty object when no extension provides metadata.
   */
  export function getRequestHeaders(): Record<string, string>;
}

// ── File System Access API (showSaveFilePicker) ─────────────────────
interface FilePickerAcceptType {
  description?: string;
  accept: Record<string, string | string[]>;
}

interface SaveFilePickerOptions {
  suggestedName?: string;
  types?: FilePickerAcceptType[];
  excludeAcceptAllOption?: boolean;
}

interface FileSystemWritableFileStream extends WritableStream {
  write(data: Blob | File | string | BufferSource): Promise<void>;
  seek(position: number): Promise<void>;
  truncate(size: number): Promise<void>;
  close(): Promise<void>;
}

interface FileSystemFileHandle {
  createWritable(options?: {
    keepExistingData?: boolean;
  }): Promise<FileSystemWritableFileStream>;
}

interface Window {
  showSaveFilePicker(
    options?: SaveFilePickerOptions,
  ): Promise<FileSystemFileHandle>;
}
