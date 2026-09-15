"use strict";

exports.__esModule = true;
exports.default = useFocusManager;
var _react = require("react");
var _useEventCallback = _interopRequireDefault(require("./useEventCallback"));
var _useMounted = _interopRequireDefault(require("./useMounted"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/**
 * useFocusManager provides a way to track and manage focus as it moves around
 * a container element. An `onChange` is fired when focus enters or leaves the
 * element, but not when it moves around inside the element, similar to
 * `pointerenter` and `pointerleave` DOM events.
 *
 * ```tsx
 * const [focused, setFocusState] = useState(false)
 *
 * const { onBlur, onFocus } = useFocusManager({
 *   onChange: nextFocused => setFocusState(nextFocused)
 * })
 *
 * return (
 *   <div tabIndex="-1" onFocus={onFocus} onBlur={onBlur}>
 *     {String(focused)}
 *     <input />
 *     <input />
 *
 *     <button>A button</button>
 *   </div>
 * ```
 *
 * @returns a memoized FocusController containing event handlers
 */
function useFocusManager(opts) {
  const isMounted = (0, _useMounted.default)();
  const lastFocused = (0, _react.useRef)();
  const handle = (0, _react.useRef)();
  const willHandle = (0, _useEventCallback.default)(opts.willHandle);
  const didHandle = (0, _useEventCallback.default)(opts.didHandle);
  const onChange = (0, _useEventCallback.default)(opts.onChange);
  const isDisabled = (0, _useEventCallback.default)(opts.isDisabled);
  const handleChange = (0, _react.useCallback)((focused, event) => {
    if (focused !== lastFocused.current) {
      didHandle == null ? void 0 : didHandle(focused, event);

      // only fire a change when unmounted if its a blur
      if (isMounted() || !focused) {
        lastFocused.current = focused;
        onChange == null ? void 0 : onChange(focused, event);
      }
    }
  }, [isMounted, didHandle, onChange, lastFocused]);
  const handleFocusChange = (0, _react.useCallback)((focused, event) => {
    if (isDisabled()) return;
    if (event && event.persist) event.persist();
    if ((willHandle == null ? void 0 : willHandle(focused, event)) === false) {
      return;
    }
    clearTimeout(handle.current);
    if (focused) {
      handleChange(focused, event);
    } else {
      handle.current = window.setTimeout(() => handleChange(focused, event));
    }
  }, [willHandle, handleChange]);
  return (0, _react.useMemo)(() => ({
    onBlur: event => {
      handleFocusChange(false, event);
    },
    onFocus: event => {
      handleFocusChange(true, event);
    }
  }), [handleFocusChange]);
}