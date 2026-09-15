/// <reference types="react" />
export declare const WindowProvider: import("react").Provider<(Window & typeof globalThis) | undefined>;
/**
 * The document "window" placed in React context. Helpful for determining
 * SSR context, or when rendering into an iframe.
 *
 * @returns the current window
 */
export default function useWindow(): (Window & typeof globalThis) | undefined;
