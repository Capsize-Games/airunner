"use strict";

exports.__esModule = true;
exports.default = useDebouncedState;
var _react = require("react");
var _useDebouncedCallback = _interopRequireDefault(require("./useDebouncedCallback"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/**
 * Similar to `useState`, except the setter function is debounced by
 * the specified delay. Unlike `useState`, the returned setter is not "pure" having
 * the side effect of scheduling an update in a timeout, which makes it unsafe to call
 * inside of the component render phase.
 *
 * ```ts
 * const [value, setValue] = useDebouncedState('test', 500)
 *
 * setValue('test2')
 * ```
 *
 * @param initialState initial state value
 * @param delayOrOptions The milliseconds delay before a new value is set, or options object
 */
function useDebouncedState(initialState, delayOrOptions) {
  const [state, setState] = (0, _react.useState)(initialState);
  const debouncedSetState = (0, _useDebouncedCallback.default)(setState, delayOrOptions);
  return [state, debouncedSetState];
}