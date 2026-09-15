import useEventListener from './useEventListener';
import { useCallback } from 'react';
/**
 * Attaches an event handler outside directly to the `document`,
 * bypassing the react synthetic event system.
 *
 * ```ts
 * useGlobalListener('keydown', (event) => {
 *  console.log(event.key)
 * })
 * ```
 *
 * @param event The DOM event name
 * @param handler An event handler
 * @param capture Whether or not to listen during the capture event phase
 */
export default function useGlobalListener(event, handler, capture = false) {
  const documentTarget = useCallback(() => document, []);
  return useEventListener(documentTarget, event, handler, capture);
}