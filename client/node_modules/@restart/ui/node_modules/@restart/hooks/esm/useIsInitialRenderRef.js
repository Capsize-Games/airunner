import { useEffect, useLayoutEffect, useRef } from 'react';

/**
 * Returns ref that is `true` on the initial render and `false` on subsequent renders. It
 * is StrictMode safe, so will reset correctly if the component is unmounted and remounted.
 *
 * This hook *must* be used before any effects that read it's value to be accurate.
 */
export default function useIsInitialRenderRef() {
  const effectCount = useRef(0);
  const isInitialRenderRef = useRef(true);
  useLayoutEffect(() => {
    effectCount.current += 1;
    if (effectCount.current >= 2) {
      isInitialRenderRef.current = false;
    }
  });

  // Strict mode handling in React 18
  useEffect(() => () => {
    effectCount.current = 0;
    isInitialRenderRef.current = true;
  }, []);
  return isInitialRenderRef;
}