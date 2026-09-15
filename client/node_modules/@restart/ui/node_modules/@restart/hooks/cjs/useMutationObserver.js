"use strict";

exports.__esModule = true;
exports.default = void 0;
var _useCustomEffect = _interopRequireDefault(require("./useCustomEffect"));
var _dequal = require("dequal");
var _useImmediateUpdateEffect = _interopRequireDefault(require("./useImmediateUpdateEffect"));
var _useEventCallback = _interopRequireDefault(require("./useEventCallback"));
var _react = require("react");
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function isDepsEqual([nextElement, nextConfig], [prevElement, prevConfig]) {
  return nextElement === prevElement && (0, _dequal.dequal)(nextConfig, prevConfig);
}

/**
 * Observe mutations on a DOM node or tree of DOM nodes.
 * Depends on the `MutationObserver` api.
 *
 * ```tsx
 * const [element, attachRef] = useCallbackRef(null);
 *
 * useMutationObserver(element, { subtree: true }, (records) => {
 *
 * });
 *
 * return (
 *   <div ref={attachRef} />
 * )
 * ```
 *
 * @param element The DOM element to observe
 * @param config The observer configuration
 * @param callback A callback fired when a mutation occurs
 */

/**
 * Observe mutations on a DOM node or tree of DOM nodes.
 * use a `MutationObserver` and return records as the are received.
 *
 * ```tsx
 * const [element, attachRef] = useCallbackRef(null);
 *
 * const records = useMutationObserver(element, { subtree: true });
 *
 * return (
 *   <div ref={attachRef} />
 * )
 * ```
 *
 * @param element The DOM element to observe
 * @param config The observer configuration
 */

function useMutationObserver(element, config, callback) {
  const [records, setRecords] = (0, _react.useState)(null);
  const handler = (0, _useEventCallback.default)(callback || setRecords);
  (0, _useCustomEffect.default)(() => {
    if (!element) return;

    // The behavior around reusing mutation observers is confusing
    // observing again _should_ disable the last listener but doesn't
    // seem to always be the case, maybe just in JSDOM? In any case the cost
    // to redeclaring it is gonna be fairly low anyway, so make it simple
    const observer = new MutationObserver(handler);
    observer.observe(element, config);
    return () => {
      observer.disconnect();
    };
  }, [element, config], {
    isEqual: isDepsEqual,
    // Intentionally done in render, otherwise observer will miss any
    // changes made to the DOM during this update
    effectHook: _useImmediateUpdateEffect.default
  });
  return callback ? void 0 : records || [];
}
var _default = useMutationObserver;
exports.default = _default;