"use strict";

exports.__esModule = true;
exports.default = void 0;
var _react = require("react");
var _useStableMemo = _interopRequireDefault(require("./useStableMemo"));
var _useIsomorphicEffect = _interopRequireDefault(require("./useIsomorphicEffect"));
var _useEventCallback = _interopRequireDefault(require("./useEventCallback"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
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
  const [entries, setEntry] = (0, _react.useState)(null);
  const handler = (0, _useEventCallback.default)(callback || setEntry);

  // We wait for element to exist before constructing
  const observer = (0, _useStableMemo.default)(() => root !== null && typeof IntersectionObserver !== 'undefined' && new IntersectionObserver(handler, {
    threshold,
    root,
    rootMargin
  }), [handler, root, rootMargin, threshold && JSON.stringify(threshold)]);
  (0, _useIsomorphicEffect.default)(() => {
    if (!element || !observer) return;
    observer.observe(element);
    return () => {
      observer.unobserve(element);
    };
  }, [observer, element]);
  return callback ? undefined : entries || [];
}
var _default = useIntersectionObserver;
exports.default = _default;