"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _classnames = _interopRequireDefault(require("classnames"));
var _useTimeout = _interopRequireDefault(require("@restart/hooks/useTimeout"));
var _ToastFade = _interopRequireDefault(require("./ToastFade"));
var _ToastHeader = _interopRequireDefault(require("./ToastHeader"));
var _ToastBody = _interopRequireDefault(require("./ToastBody"));
var _ThemeProvider = require("./ThemeProvider");
var _ToastContext = _interopRequireDefault(require("./ToastContext"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const Toast = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  transition: Transition = _ToastFade.default,
  show = true,
  animation = true,
  delay = 5000,
  autohide = false,
  onClose,
  onEntered,
  onExit,
  onExiting,
  onEnter,
  onEntering,
  onExited,
  bg,
  ...props
}, ref) => {
  bsPrefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'toast');

  // We use refs for these, because we don't want to restart the autohide
  // timer in case these values change.
  const delayRef = (0, _react.useRef)(delay);
  const onCloseRef = (0, _react.useRef)(onClose);
  (0, _react.useEffect)(() => {
    delayRef.current = delay;
    onCloseRef.current = onClose;
  }, [delay, onClose]);
  const autohideTimeout = (0, _useTimeout.default)();
  const autohideToast = !!(autohide && show);
  const autohideFunc = (0, _react.useCallback)(() => {
    if (autohideToast) {
      onCloseRef.current == null || onCloseRef.current();
    }
  }, [autohideToast]);
  (0, _react.useEffect)(() => {
    // Only reset timer if show or autohide changes.
    autohideTimeout.set(autohideFunc, delayRef.current);
  }, [autohideTimeout, autohideFunc]);
  const toastContext = (0, _react.useMemo)(() => ({
    onClose
  }), [onClose]);
  const hasAnimation = !!(Transition && animation);
  const toast = /*#__PURE__*/(0, _jsxRuntime.jsx)("div", {
    ...props,
    ref: ref,
    className: (0, _classnames.default)(bsPrefix, className, bg && `bg-${bg}`, !hasAnimation && (show ? 'show' : 'hide')),
    role: "alert",
    "aria-live": "assertive",
    "aria-atomic": "true"
  });
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_ToastContext.default.Provider, {
    value: toastContext,
    children: hasAnimation && Transition ? /*#__PURE__*/(0, _jsxRuntime.jsx)(Transition, {
      in: show,
      onEnter: onEnter,
      onEntering: onEntering,
      onEntered: onEntered,
      onExit: onExit,
      onExiting: onExiting,
      onExited: onExited,
      unmountOnExit: true,
      children: toast
    }) : toast
  });
});
Toast.displayName = 'Toast';
var _default = exports.default = Object.assign(Toast, {
  Body: _ToastBody.default,
  Header: _ToastHeader.default
});
module.exports = exports.default;