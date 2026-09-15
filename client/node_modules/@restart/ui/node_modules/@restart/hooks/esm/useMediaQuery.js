import useEffect from './useIsomorphicEffect';
import { useState } from 'react';
const matchersByWindow = new WeakMap();
const getMatcher = (query, targetWindow) => {
  if (!query || !targetWindow) return undefined;
  const matchers = matchersByWindow.get(targetWindow) || new Map();
  matchersByWindow.set(targetWindow, matchers);
  let mql = matchers.get(query);
  if (!mql) {
    mql = targetWindow.matchMedia(query);
    mql.refCount = 0;
    matchers.set(mql.media, mql);
  }
  return mql;
};
/**
 * Match a media query and get updates as the match changes. The media string is
 * passed directly to `window.matchMedia` and run as a Layout Effect, so initial
 * matches are returned before the browser has a chance to paint.
 *
 * ```tsx
 * function Page() {
 *   const isWide = useMediaQuery('min-width: 1000px')
 *
 *   return isWide ? "very wide" : 'not so wide'
 * }
 * ```
 *
 * Media query lists are also reused globally, hook calls for the same query
 * will only create a matcher once under the hood.
 *
 * @param query A media query
 * @param targetWindow The window to match against, uses the globally available one as a default.
 */
export default function useMediaQuery(query, targetWindow = typeof window === 'undefined' ? undefined : window) {
  const mql = getMatcher(query, targetWindow);
  const [matches, setMatches] = useState(() => mql ? mql.matches : false);
  useEffect(() => {
    let mql = getMatcher(query, targetWindow);
    if (!mql) {
      return setMatches(false);
    }
    let matchers = matchersByWindow.get(targetWindow);
    const handleChange = () => {
      setMatches(mql.matches);
    };
    mql.refCount++;
    mql.addListener(handleChange);
    handleChange();
    return () => {
      mql.removeListener(handleChange);
      mql.refCount--;
      if (mql.refCount <= 0) {
        matchers == null ? void 0 : matchers.delete(mql.media);
      }
      mql = undefined;
    };
  }, [query]);
  return matches;
}