"use strict";

exports.__esModule = true;
exports.default = void 0;
var _react = require("react");
var _useDebouncedState = _interopRequireDefault(require("./useDebouncedState"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
const defaultIsEqual = (a, b) => a === b;
/**
 * Debounce a value change by a specified number of milliseconds. Useful
 * when you want need to trigger a change based on a value change, but want
 * to defer changes until the changes reach some level of infrequency.
 *
 * @param value
 * @param waitOrOptions
 * @returns
 */
function useDebouncedValue(value, waitOrOptions = 500) {
  const previousValueRef = (0, _react.useRef)(value);
  const isEqual = typeof waitOrOptions === 'object' ? waitOrOptions.isEqual || defaultIsEqual : defaultIsEqual;
  const [debouncedValue, setDebouncedValue] = (0, _useDebouncedState.default)(value, waitOrOptions);
  (0, _react.useDebugValue)(debouncedValue);
  (0, _react.useEffect)(() => {
    if (!isEqual || !isEqual(previousValueRef.current, value)) {
      previousValueRef.current = value;
      setDebouncedValue(value);
    }
  });
  return debouncedValue;
}
var _default = useDebouncedValue;
exports.default = _default;