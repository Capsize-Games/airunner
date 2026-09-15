"use strict";

exports.__esModule = true;
exports.default = useAnimationFrame;
var _react = require("react");
var _useMounted = _interopRequireDefault(require("./useMounted"));
var _useStableMemo = _interopRequireDefault(require("./useStableMemo"));
var _useWillUnmount = _interopRequireDefault(require("./useWillUnmount"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/**
 * Returns a controller object for requesting and cancelling an animation freame that is properly cleaned up
 * once the component unmounts. New requests cancel and replace existing ones.
 *
 * ```ts
 * const [style, setStyle] = useState({});
 * const animationFrame = useAnimationFrame();
 *
 * const handleMouseMove = (e) => {
 *   animationFrame.request(() => {
 *     setStyle({ top: e.clientY, left: e.clientY })
 *   })
 * }
 *
 * const handleMouseUp = () => {
 *   animationFrame.cancel()
 * }
 *
 * return (
 *   <div onMouseUp={handleMouseUp} onMouseMove={handleMouseMove}>
 *     <Ball style={style} />
 *   </div>
 * )
 * ```
 */
function useAnimationFrame() {
  const isMounted = (0, _useMounted.default)();
  const handle = (0, _react.useRef)();
  const cancel = () => {
    if (handle.current != null) {
      cancelAnimationFrame(handle.current);
    }
  };
  (0, _useWillUnmount.default)(cancel);
  return (0, _useStableMemo.default)(() => ({
    request(cancelPrevious, fn) {
      if (!isMounted()) return;
      if (cancelPrevious) cancel();
      handle.current = requestAnimationFrame(fn || cancelPrevious);
    },
    cancel
  }), []);
}