"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var React = _interopRequireWildcard(require("react"));
var _uncontrollable = require("uncontrollable");
var _useEventCallback = _interopRequireDefault(require("@restart/hooks/useEventCallback"));
var _ThemeProvider = require("./ThemeProvider");
var _AlertHeading = _interopRequireDefault(require("./AlertHeading"));
var _AlertLink = _interopRequireDefault(require("./AlertLink"));
var _Fade = _interopRequireDefault(require("./Fade"));
var _CloseButton = _interopRequireDefault(require("./CloseButton"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const Alert = /*#__PURE__*/React.forwardRef((uncontrolledProps, ref) => {
  const {
    bsPrefix,
    show = true,
    closeLabel = 'Close alert',
    closeVariant,
    className,
    children,
    variant = 'primary',
    onClose,
    dismissible,
    transition = _Fade.default,
    ...props
  } = (0, _uncontrollable.useUncontrolled)(uncontrolledProps, {
    show: 'onClose'
  });
  const prefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'alert');
  const handleClose = (0, _useEventCallback.default)(e => {
    if (onClose) {
      onClose(false, e);
    }
  });
  const Transition = transition === true ? _Fade.default : transition;
  const alert = /*#__PURE__*/(0, _jsxRuntime.jsxs)("div", {
    role: "alert",
    ...(!Transition ? props : undefined),
    ref: ref,
    className: (0, _classnames.default)(className, prefix, variant && `${prefix}-${variant}`, dismissible && `${prefix}-dismissible`),
    children: [dismissible && /*#__PURE__*/(0, _jsxRuntime.jsx)(_CloseButton.default, {
      onClick: handleClose,
      "aria-label": closeLabel,
      variant: closeVariant
    }), children]
  });
  if (!Transition) return show ? alert : null;
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(Transition, {
    unmountOnExit: true,
    ...props,
    ref: undefined,
    in: show,
    children: alert
  });
});
Alert.displayName = 'Alert';
var _default = exports.default = Object.assign(Alert, {
  Link: _AlertLink.default,
  Heading: _AlertHeading.default
});
module.exports = exports.default;