"use strict";

exports.__esModule = true;
exports.default = useTimeout;
var _react = require("react");
var _useMounted = _interopRequireDefault(require("./useMounted"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/*
 * Browsers including Internet Explorer, Chrome, Safari, and Firefox store the
 * delay as a 32-bit signed integer internally. This causes an integer overflow
 * when using delays larger than 2,147,483,647 ms (about 24.8 days),
 * resulting in the timeout being executed immediately.
 *
 * via: https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/setTimeout
 */
const MAX_DELAY_MS = 2 ** 31 - 1;
function setChainedTimeout(handleRef, fn, timeoutAtMs) {
  const delayMs = timeoutAtMs - Date.now();
  handleRef.current = delayMs <= MAX_DELAY_MS ? setTimeout(fn, delayMs) : setTimeout(() => setChainedTimeout(handleRef, fn, timeoutAtMs), MAX_DELAY_MS);
}
/**
 * Returns a controller object for setting a timeout that is properly cleaned up
 * once the component unmounts. New timeouts cancel and replace existing ones.
 *
 * ```tsx
 * const { set, clear } = useTimeout();
 * const [hello, showHello] = useState(false);
 * //Display hello after 5 seconds
 * set(() => showHello(true), 5000);
 * return (
 *   <div className="App">
 *     {hello ? <h3>Hello</h3> : null}
 *   </div>
 * );
 * ```
 */
function useTimeout() {
  const [timeout, setTimeoutState] = (0, _react.useState)(null);
  const isMounted = (0, _useMounted.default)();

  // types are confused between node and web here IDK
  const handleRef = (0, _react.useRef)(null);
  (0, _react.useEffect)(() => {
    if (!timeout) {
      return;
    }
    const {
      fn,
      delayMs
    } = timeout;
    function task() {
      if (isMounted()) {
        setTimeoutState(null);
      }
      fn();
    }
    if (delayMs <= MAX_DELAY_MS) {
      // For simplicity, if the timeout is short, just set a normal timeout.
      handleRef.current = setTimeout(task, delayMs);
    } else {
      setChainedTimeout(handleRef, task, Date.now() + delayMs);
    }
    const handle = handleRef.current;
    return () => {
      // this should be a no-op since they are either the same or `handle`
      // already expired but no harm in calling twice
      if (handleRef.current !== handle) {
        clearTimeout(handle);
      }
      clearTimeout(handleRef.current);
      handleRef.current === null;
    };
  }, [timeout]);
  const isPending = !!timeout;
  return (0, _react.useMemo)(() => {
    return {
      set(fn, delayMs = 0) {
        if (!isMounted()) return;
        setTimeoutState({
          fn,
          delayMs
        });
      },
      clear() {
        setTimeoutState(null);
      },
      isPending,
      handleRef
    };
  }, [isPending, setTimeoutState, handleRef, isMounted]);
}