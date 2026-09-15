"use strict";

exports.__esModule = true;
exports.default = useThrottledEventHandler;
var _react = require("react");
var _useMounted = _interopRequireDefault(require("./useMounted"));
var _useEventCallback = _interopRequireDefault(require("./useEventCallback"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
const isSyntheticEvent = event => typeof event.persist === 'function';
/**
 * Creates a event handler function throttled by `requestAnimationFrame` that
 * returns the **most recent** event. Useful for noisy events that update react state.
 *
 * ```tsx
 * function Component() {
 *   const [position, setPosition] = useState();
 *   const handleMove = useThrottledEventHandler<React.PointerEvent>(
 *     (event) => {
 *       setPosition({
 *         top: event.clientX,
 *         left: event.clientY,
 *       })
 *     }
 *   )
 *
 *   return (
 *     <div onPointerMove={handleMove}>
 *        <div style={position} />
 *     </div>
 *   );
 * }
 * ```
 *
 * @param handler An event handler function
 * @typeParam TEvent The event object passed to the handler function
 * @returns The event handler with a `clear` method attached for clearing any in-flight handler calls
 *
 */
function useThrottledEventHandler(handler) {
  const isMounted = (0, _useMounted.default)();
  const eventHandler = (0, _useEventCallback.default)(handler);
  const nextEventInfoRef = (0, _react.useRef)({
    event: null,
    handle: null
  });
  const clear = () => {
    cancelAnimationFrame(nextEventInfoRef.current.handle);
    nextEventInfoRef.current.handle = null;
  };
  const handlePointerMoveAnimation = () => {
    const {
      current: next
    } = nextEventInfoRef;
    if (next.handle && next.event) {
      if (isMounted()) {
        next.handle = null;
        eventHandler(next.event);
      }
    }
    next.event = null;
  };
  const throttledHandler = event => {
    if (!isMounted()) return;
    if (isSyntheticEvent(event)) {
      event.persist();
    }
    // Special handling for a React.Konva event which reuses the
    // event object as it bubbles, setting target
    else if ('evt' in event) {
      event = Object.assign({}, event);
    }
    nextEventInfoRef.current.event = event;
    if (!nextEventInfoRef.current.handle) {
      nextEventInfoRef.current.handle = requestAnimationFrame(handlePointerMoveAnimation);
    }
  };
  throttledHandler.clear = clear;
  return throttledHandler;
}