"use strict";

exports.__esModule = true;
exports.default = void 0;
var _useCallbackRef = _interopRequireDefault(require("@restart/hooks/useCallbackRef"));
var React = _interopRequireWildcard(require("react"));
var _useWaypoint = _interopRequireWildcard(require("./useWaypoint"));
exports.Position = _useWaypoint.Position;
var _jsxRuntime = require("react/jsx-runtime");
const _excluded = ["renderComponent", "onPositionChange"];
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && {}.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function _interopRequireDefault(e) { return e && e.__esModule ? e : { default: e }; }
function _objectWithoutPropertiesLoose(r, e) { if (null == r) return {}; var t = {}; for (var n in r) if ({}.hasOwnProperty.call(r, n)) { if (e.indexOf(n) >= 0) continue; t[n] = r[n]; } return t; }
const defaultRenderComponent = ref => /*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
  ref: ref,
  style: {
    fontSize: 0
  }
});
/**
 * A component that tracks when it enters or leaves the viewport. Implemented
 * using IntersectionObserver, polyfill may be required for older browsers.
 */
function Waypoint(_ref) {
  let {
      renderComponent = defaultRenderComponent,
      onPositionChange
    } = _ref,
    options = _objectWithoutPropertiesLoose(_ref, _excluded);
  const [element, setElement] = (0, _useCallbackRef.default)();
  (0, _useWaypoint.default)(element, onPositionChange, options);
  return renderComponent(setElement);
}
var _default = exports.default = Waypoint;