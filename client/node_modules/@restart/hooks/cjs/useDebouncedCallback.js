"use strict";

exports.__esModule = true;
exports.default = void 0;
var _react = require("react");
var _useTimeout = _interopRequireDefault(require("./useTimeout"));
var _useEventCallback = _interopRequireDefault(require("./useEventCallback"));
var _useWillUnmount = _interopRequireDefault(require("./useWillUnmount"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/**
 * Creates a debounced function that will invoke the input function after the
 * specified wait.
 *
 * > Heads up! debounced functions are not pure since they are called in a timeout
 * > Don't call them inside render.
 *
 * @param fn a function that will be debounced
 * @param waitOrOptions a wait in milliseconds or a debounce configuration
 */

/**
 * Creates a debounced function that will invoke the input function after the
 * specified wait.
 *
 * > Heads up! debounced functions are not pure since they are called in a timeout
 * > Don't call them inside render.
 *
 * @param fn a function that will be debounced
 * @param waitOrOptions a wait in milliseconds or a debounce configuration
 */

function useDebouncedCallback(fn, waitOrOptions) {
  const lastCallTimeRef = (0, _react.useRef)(null);
  const lastInvokeTimeRef = (0, _react.useRef)(0);
  const returnValueRef = (0, _react.useRef)();
  const isTimerSetRef = (0, _react.useRef)(false);
  const lastArgsRef = (0, _react.useRef)(null);
  // Use any to bypass type issue with setTimeout.
  const timerRef = (0, _react.useRef)(0);
  const handleCallback = (0, _useEventCallback.default)(fn);
  const {
    wait,
    maxWait,
    leading = false,
    trailing = true
  } = typeof waitOrOptions === 'number' ? {
    wait: waitOrOptions
  } : waitOrOptions;
  const timeout = (0, _useTimeout.default)();
  (0, _useWillUnmount.default)(() => {
    clearTimeout(timerRef.current);
    isTimerSetRef.current = false;
  });
  return (0, _react.useMemo)(() => {
    const hasMaxWait = !!maxWait;
    function leadingEdge(time) {
      // Reset any `maxWait` timer.
      lastInvokeTimeRef.current = time;

      // Start the timer for the trailing edge.
      isTimerSetRef.current = true;
      timeout.set(timerExpired, wait);
      if (!leading) {
        return returnValueRef.current;
      }
      return invokeFunc(time);
    }
    function trailingEdge(time) {
      isTimerSetRef.current = false;

      // Only invoke if we have `lastArgs` which means `func` has been
      // debounced at least once.
      if (trailing && lastArgsRef.current) {
        return invokeFunc(time);
      }
      lastArgsRef.current = null;
      return returnValueRef.current;
    }
    function timerExpired() {
      var _lastCallTimeRef$curr;
      var time = Date.now();
      if (shouldInvoke(time)) {
        return trailingEdge(time);
      }
      const timeSinceLastCall = time - ((_lastCallTimeRef$curr = lastCallTimeRef.current) != null ? _lastCallTimeRef$curr : 0);
      const timeSinceLastInvoke = time - lastInvokeTimeRef.current;
      const timeWaiting = wait - timeSinceLastCall;

      // Restart the timer.
      timeout.set(timerExpired, hasMaxWait ? Math.min(timeWaiting, maxWait - timeSinceLastInvoke) : timeWaiting);
    }
    function invokeFunc(time) {
      var _lastArgsRef$current;
      const args = (_lastArgsRef$current = lastArgsRef.current) != null ? _lastArgsRef$current : [];
      lastArgsRef.current = null;
      lastInvokeTimeRef.current = time;
      const retValue = handleCallback(...args);
      returnValueRef.current = retValue;
      return retValue;
    }
    function shouldInvoke(time) {
      var _lastCallTimeRef$curr2;
      const timeSinceLastCall = time - ((_lastCallTimeRef$curr2 = lastCallTimeRef.current) != null ? _lastCallTimeRef$curr2 : 0);
      const timeSinceLastInvoke = time - lastInvokeTimeRef.current;

      // Either this is the first call, activity has stopped and we're at the
      // trailing edge, the system time has gone backwards and we're treating
      // it as the trailing edge, or we've hit the `maxWait` limit.
      return lastCallTimeRef.current === null || timeSinceLastCall >= wait || timeSinceLastCall < 0 || hasMaxWait && timeSinceLastInvoke >= maxWait;
    }
    return (...args) => {
      const time = Date.now();
      const isInvoking = shouldInvoke(time);
      lastArgsRef.current = args;
      lastCallTimeRef.current = time;
      if (isInvoking) {
        if (!isTimerSetRef.current) {
          return leadingEdge(lastCallTimeRef.current);
        }
        if (hasMaxWait) {
          // Handle invocations in a tight loop.
          isTimerSetRef.current = true;
          timerRef.current = setTimeout(timerExpired, wait);
          return invokeFunc(lastCallTimeRef.current);
        }
      }
      if (!isTimerSetRef.current) {
        isTimerSetRef.current = true;
        timerRef.current = setTimeout(timerExpired, wait);
      }
      return returnValueRef.current;
    };
  }, [handleCallback, wait, maxWait, leading, trailing]);
}
var _default = useDebouncedCallback;
exports.default = _default;