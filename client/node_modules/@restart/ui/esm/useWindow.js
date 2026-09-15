import { createContext, useContext } from 'react';
import canUseDOM from 'dom-helpers/canUseDOM';
const Context = /*#__PURE__*/createContext(canUseDOM ? window : undefined);
export const WindowProvider = Context.Provider;

/**
 * The document "window" placed in React context. Helpful for determining
 * SSR context, or when rendering into an iframe.
 *
 * @returns the current window
 */
export default function useWindow() {
  return useContext(Context);
}