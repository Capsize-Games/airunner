"use strict";

exports.__esModule = true;
exports.default = useAnimationFrame;
var _react = require("react");
var _useMounted = _interopRequireDefault(require("./useMounted"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/**
 * Returns a controller object for requesting and cancelling an animation frame that is properly cleaned up
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
  const [animationFrame, setAnimationFrameState] = (0, _react.useState)(null);
  (0, _react.useEffect)(() => {
    if (!animationFrame) {
      return;
    }
    const {
      fn
    } = animationFrame;
    const handle = requestAnimationFrame(fn);
    return () => {
      cancelAnimationFrame(handle);
    };
  }, [animationFrame]);
  const [returnValue] = (0, _react.useState)(() => ({
    request(callback) {
      if (!isMounted()) return;
      setAnimationFrameState({
        fn: callback
      });
    },
    cancel: () => {
      if (!isMounted()) return;
      setAnimationFrameState(null);
    }
  }));
  return returnValue;
}