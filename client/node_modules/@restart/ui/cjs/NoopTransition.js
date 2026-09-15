"use strict";

exports.__esModule = true;
exports.default = void 0;
var _useEventCallback = _interopRequireDefault(require("@restart/hooks/useEventCallback"));
var _useMergedRefs = _interopRequireDefault(require("@restart/hooks/useMergedRefs"));
var _react = require("react");
var _utils = require("./utils");
function _interopRequireDefault(e) { return e && e.__esModule ? e : { default: e }; }
function NoopTransition({
  children,
  in: inProp,
  onExited,
  mountOnEnter,
  unmountOnExit
}) {
  const ref = (0, _react.useRef)(null);
  const hasEnteredRef = (0, _react.useRef)(inProp);
  const handleExited = (0, _useEventCallback.default)(onExited);
  (0, _react.useEffect)(() => {
    if (inProp) hasEnteredRef.current = true;else {
      handleExited(ref.current);
    }
  }, [inProp, handleExited]);
  const combinedRef = (0, _useMergedRefs.default)(ref, (0, _utils.getChildRef)(children));
  const child = /*#__PURE__*/(0, _react.cloneElement)(children, {
    ref: combinedRef
  });
  if (inProp) return child;
  if (unmountOnExit) {
    return null;
  }
  if (!hasEnteredRef.current && mountOnEnter) {
    return null;
  }
  return child;
}
var _default = exports.default = NoopTransition;