import { useState } from 'react';
import useStableMemo from './useStableMemo';
import useEffect from './useIsomorphicEffect';
import useEventCallback from './useEventCallback';

/**
 * Setup an [`IntersectionObserver`](https://developer.mozilla.org/en-US/docs/Web/API/IntersectionObserver) on
 * a DOM Element that returns it's entries as they arrive.
 *
 * @param element The DOM element to observe
 * @param init IntersectionObserver options with a notable change,
 * unlike a plain IntersectionObserver `root: null` means "not provided YET",
 * and the hook will wait until it receives a non-null value to set up the observer.
 * This change allows for easier syncing of element and root values in a React
 * context.
 */

/**
 * Setup an [`IntersectionObserver`](https://developer.mozilla.org/en-US/docs/Web/API/IntersectionObserver) on
 * a DOM Element. This overload does not trigger component updates when receiving new
 * entries. This allows for finer grained performance optimizations by the consumer.
 *
 * @param element The DOM element to observe
 * @param callback A listener for intersection updates.
 * @param init IntersectionObserver options with a notable change,
 * unlike a plain IntersectionObserver `root: null` means "not provided YET",
 * and the hook will wait until it receives a non-null value to set up the observer.
 * This change allows for easier syncing of element and root values in a React
 * context.
 *
 */

function useIntersectionObserver(element, callbackOrOptions, maybeOptions) {
  let callback;
  let options;
  if (typeof callbackOrOptions === 'function') {
    callback = callbackOrOptions;
    options = maybeOptions || {};
  } else {
    options = callbackOrOptions || {};
  }
  const {
    threshold,
    root,
    rootMargin
  } = options;
  const [entries, setEntry] = useState(null);
  const handler = useEventCallback(callback || setEntry);

  // We wait for element to exist before constructing
  const observer = useStableMemo(() => root !== null && typeof IntersectionObserver !== 'undefined' && new IntersectionObserver(handler, {
    threshold,
    root,
    rootMargin
  }), [handler, root, rootMargin, threshold && JSON.stringify(threshold)]);
  useEffect(() => {
    if (!element || !observer) return;
    observer.observe(element);
    return () => {
      observer.unobserve(element);
    };
  }, [observer, element]);
  return callback ? undefined : entries || [];
}
export default useIntersectionObserver;