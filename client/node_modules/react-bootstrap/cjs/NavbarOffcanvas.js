"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _useEventCallback = _interopRequireDefault(require("@restart/hooks/useEventCallback"));
var _Offcanvas = _interopRequireDefault(require("./Offcanvas"));
var _NavbarContext = _interopRequireDefault(require("./NavbarContext"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const NavbarOffcanvas = /*#__PURE__*/React.forwardRef(({
  onHide,
  ...props
}, ref) => {
  const context = (0, _react.useContext)(_NavbarContext.default);
  const handleHide = (0, _useEventCallback.default)(() => {
    context == null || context.onToggle == null || context.onToggle();
    onHide == null || onHide();
  });
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_Offcanvas.default, {
    ref: ref,
    show: !!(context != null && context.expanded),
    ...props,
    renderStaticNode: true,
    onHide: handleHide
  });
});
NavbarOffcanvas.displayName = 'NavbarOffcanvas';
var _default = exports.default = NavbarOffcanvas;
module.exports = exports.default;