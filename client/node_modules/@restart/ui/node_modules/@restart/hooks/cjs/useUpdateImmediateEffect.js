"use strict";

exports.__esModule = true;
exports.default = void 0;
var _react = require("react");
var _useStableMemo = _interopRequireDefault(require("./useStableMemo"));
var _useWillUnmount = _interopRequireDefault(require("./useWillUnmount"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/**
 * An _immediate_ effect that runs an effect callback when its dependency array
 * changes. This is helpful for updates should must run during render, most
 * commonly state derived from props; a more ergonomic version of https://reactjs.org/docs/hooks-faq.html#how-do-i-implement-getderivedstatefromprops
 *
 * ```ts
 * function Example({ value }) {
 *   const [intermediaryValue, setValue] = useState(value);
 *
 *   useUpdateImmediateEffect(() => {
 *     setValue(value)
 *   }, [value])
 * ```
 *
 * @category effects
 */
function useUpdateImmediateEffect(effect, deps) {
  const firstRef = (0, _react.useRef)(true);
  const tearDown = (0, _react.useRef)();
  (0, _useWillUnmount.default)(() => {
    if (tearDown.current) tearDown.current();
  });
  (0, _useStableMemo.default)(() => {
    if (firstRef.current) {
      firstRef.current = false;
      return;
    }
    if (tearDown.current) tearDown.current();
    tearDown.current = effect();
  }, deps);
}
var _default = useUpdateImmediateEffect;
exports.default = _default;