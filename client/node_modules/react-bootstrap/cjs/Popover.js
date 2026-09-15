"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var React = _interopRequireWildcard(require("react"));
var _ThemeProvider = require("./ThemeProvider");
var _PopoverHeader = _interopRequireDefault(require("./PopoverHeader"));
var _PopoverBody = _interopRequireDefault(require("./PopoverBody"));
var _helpers = require("./helpers");
var _getInitialPopperStyles = _interopRequireDefault(require("./getInitialPopperStyles"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const Popover = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  placement = 'right',
  className,
  style,
  children,
  body,
  arrowProps,
  hasDoneInitialMeasure,
  popper,
  show,
  ...props
}, ref) => {
  const decoratedBsPrefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'popover');
  const isRTL = (0, _ThemeProvider.useIsRTL)();
  const [primaryPlacement] = (placement == null ? void 0 : placement.split('-')) || [];
  const bsDirection = (0, _helpers.getOverlayDirection)(primaryPlacement, isRTL);
  let computedStyle = style;
  if (show && !hasDoneInitialMeasure) {
    computedStyle = {
      ...style,
      ...(0, _getInitialPopperStyles.default)(popper == null ? void 0 : popper.strategy)
    };
  }
  return /*#__PURE__*/(0, _jsxRuntime.jsxs)("div", {
    ref: ref,
    role: "tooltip",
    style: computedStyle,
    "x-placement": primaryPlacement,
    className: (0, _classnames.default)(className, decoratedBsPrefix, primaryPlacement && `bs-popover-${bsDirection}`),
    ...props,
    children: [/*#__PURE__*/(0, _jsxRuntime.jsx)("div", {
      className: "popover-arrow",
      ...arrowProps
    }), body ? /*#__PURE__*/(0, _jsxRuntime.jsx)(_PopoverBody.default, {
      children: children
    }) : children]
  });
});
Popover.displayName = 'Popover';
var _default = exports.default = Object.assign(Popover, {
  Header: _PopoverHeader.default,
  Body: _PopoverBody.default,
  // Default popover offset.
  // https://github.com/twbs/bootstrap/blob/5c32767e0e0dbac2d934bcdee03719a65d3f1187/js/src/popover.js#L28
  POPPER_OFFSET: [0, 8]
});
module.exports = exports.default;