"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _contains = _interopRequireDefault(require("dom-helpers/contains"));
var _propTypes = _interopRequireDefault(require("prop-types"));
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _useTimeout = _interopRequireDefault(require("@restart/hooks/useTimeout"));
var _warning = _interopRequireDefault(require("warning"));
var _uncontrollable = require("uncontrollable");
var _useMergedRefs = _interopRequireDefault(require("@restart/hooks/useMergedRefs"));
var _utils = require("@restart/ui/utils");
var _Overlay = _interopRequireDefault(require("./Overlay"));
var _safeFindDOMNode = _interopRequireDefault(require("./safeFindDOMNode"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function normalizeDelay(delay) {
  return delay && typeof delay === 'object' ? delay : {
    show: delay,
    hide: delay
  };
}

// Simple implementation of mouseEnter and mouseLeave.
// React's built version is broken: https://github.com/facebook/react/issues/4251
// for cases when the trigger is disabled and mouseOut/Over can cause flicker
// moving from one child element to another.
function handleMouseOverOut(handler, args, relatedNative) {
  const [e] = args;
  const target = e.currentTarget;
  const related = e.relatedTarget || e.nativeEvent[relatedNative];
  if ((!related || related !== target) && !(0, _contains.default)(target, related)) {
    handler(...args);
  }
}
const triggerType = _propTypes.default.oneOf(['click', 'hover', 'focus']);
const OverlayTrigger = ({
  trigger = ['hover', 'focus'],
  overlay,
  children,
  popperConfig = {},
  show: propsShow,
  defaultShow = false,
  onToggle,
  delay: propsDelay,
  placement,
  flip = placement && placement.indexOf('auto') !== -1,
  ...props
}) => {
  const triggerNodeRef = (0, _react.useRef)(null);
  const mergedRef = (0, _useMergedRefs.default)(triggerNodeRef, (0, _utils.getChildRef)(children));
  const timeout = (0, _useTimeout.default)();
  const hoverStateRef = (0, _react.useRef)('');
  const [show, setShow] = (0, _uncontrollable.useUncontrolledProp)(propsShow, defaultShow, onToggle);
  const delay = normalizeDelay(propsDelay);
  const {
    onFocus,
    onBlur,
    onClick
  } = typeof children !== 'function' ? React.Children.only(children).props : {};
  const attachRef = r => {
    mergedRef((0, _safeFindDOMNode.default)(r));
  };
  const handleShow = (0, _react.useCallback)(() => {
    timeout.clear();
    hoverStateRef.current = 'show';
    if (!delay.show) {
      setShow(true);
      return;
    }
    timeout.set(() => {
      if (hoverStateRef.current === 'show') setShow(true);
    }, delay.show);
  }, [delay.show, setShow, timeout]);
  const handleHide = (0, _react.useCallback)(() => {
    timeout.clear();
    hoverStateRef.current = 'hide';
    if (!delay.hide) {
      setShow(false);
      return;
    }
    timeout.set(() => {
      if (hoverStateRef.current === 'hide') setShow(false);
    }, delay.hide);
  }, [delay.hide, setShow, timeout]);
  const handleFocus = (0, _react.useCallback)((...args) => {
    handleShow();
    onFocus == null || onFocus(...args);
  }, [handleShow, onFocus]);
  const handleBlur = (0, _react.useCallback)((...args) => {
    handleHide();
    onBlur == null || onBlur(...args);
  }, [handleHide, onBlur]);
  const handleClick = (0, _react.useCallback)((...args) => {
    setShow(!show);
    onClick == null || onClick(...args);
  }, [onClick, setShow, show]);
  const handleMouseOver = (0, _react.useCallback)((...args) => {
    handleMouseOverOut(handleShow, args, 'fromElement');
  }, [handleShow]);
  const handleMouseOut = (0, _react.useCallback)((...args) => {
    handleMouseOverOut(handleHide, args, 'toElement');
  }, [handleHide]);
  const triggers = trigger == null ? [] : [].concat(trigger);
  const triggerProps = {
    ref: attachRef
  };
  if (triggers.indexOf('click') !== -1) {
    triggerProps.onClick = handleClick;
  }
  if (triggers.indexOf('focus') !== -1) {
    triggerProps.onFocus = handleFocus;
    triggerProps.onBlur = handleBlur;
  }
  if (triggers.indexOf('hover') !== -1) {
    process.env.NODE_ENV !== "production" ? (0, _warning.default)(triggers.length > 1, '[react-bootstrap] Specifying only the `"hover"` trigger limits the visibility of the overlay to just mouse users. Consider also including the `"focus"` trigger so that touch and keyboard only users can see the overlay as well.') : void 0;
    triggerProps.onMouseOver = handleMouseOver;
    triggerProps.onMouseOut = handleMouseOut;
  }
  return /*#__PURE__*/(0, _jsxRuntime.jsxs)(_jsxRuntime.Fragment, {
    children: [typeof children === 'function' ? children(triggerProps) : /*#__PURE__*/(0, _react.cloneElement)(children, triggerProps), /*#__PURE__*/(0, _jsxRuntime.jsx)(_Overlay.default, {
      ...props,
      show: show,
      onHide: handleHide,
      flip: flip,
      placement: placement,
      popperConfig: popperConfig,
      target: triggerNodeRef.current,
      children: overlay
    })]
  });
};
var _default = exports.default = OverlayTrigger;
module.exports = exports.default;