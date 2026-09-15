"use strict";

exports.__esModule = true;
exports.default = useWillUnmount;
var _useUpdatedRef = _interopRequireDefault(require("./useUpdatedRef"));
var _react = require("react");
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/**
 * Attach a callback that fires when a component unmounts
 *
 * @param fn Handler to run when the component unmounts
 * @deprecated Use `useMounted` and normal effects, this is not StrictMode safe
 * @category effects
 */
function useWillUnmount(fn) {
  const onUnmount = (0, _useUpdatedRef.default)(fn);
  (0, _react.useEffect)(() => () => onUnmount.current(), []);
}