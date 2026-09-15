"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _classnames = _interopRequireDefault(require("classnames"));
var _Overlay = _interopRequireDefault(require("@restart/ui/Overlay"));
var _useEventCallback = _interopRequireDefault(require("@restart/hooks/useEventCallback"));
var _useIsomorphicEffect = _interopRequireDefault(require("@restart/hooks/useIsomorphicEffect"));
var _useMergedRefs = _interopRequireDefault(require("@restart/hooks/useMergedRefs"));
var _useOverlayOffset = _interopRequireDefault(require("./useOverlayOffset"));
var _Fade = _interopRequireDefault(require("./Fade"));
var _safeFindDOMNode = _interopRequireDefault(require("./safeFindDOMNode"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function wrapRefs(props, arrowProps) {
  const {
    ref
  } = props;
  const {
    ref: aRef
  } = arrowProps;
  props.ref = ref.__wrapped || (ref.__wrapped = r => ref((0, _safeFindDOMNode.default)(r)));
  arrowProps.ref = aRef.__wrapped || (aRef.__wrapped = r => aRef((0, _safeFindDOMNode.default)(r)));
}
const Overlay = /*#__PURE__*/React.forwardRef(({
  children: overlay,
  transition = _Fade.default,
  popperConfig = {},
  rootClose = false,
  placement = 'top',
  show: outerShow = false,
  ...outerProps
}, outerRef) => {
  const popperRef = (0, _react.useRef)({});
  const [firstRenderedState, setFirstRenderedState] = (0, _react.useState)(null);
  const [ref, modifiers] = (0, _useOverlayOffset.default)(outerProps.offset);
  const mergedRef = (0, _useMergedRefs.default)(outerRef, ref);
  const actualTransition = transition === true ? _Fade.default : transition || undefined;
  const handleFirstUpdate = (0, _useEventCallback.default)(state => {
    setFirstRenderedState(state);
    popperConfig == null || popperConfig.onFirstUpdate == null || popperConfig.onFirstUpdate(state);
  });
  (0, _useIsomorphicEffect.default)(() => {
    if (firstRenderedState && outerProps.target) {
      // Must wait for target element to resolve before updating popper.
      popperRef.current.scheduleUpdate == null || popperRef.current.scheduleUpdate();
    }
  }, [firstRenderedState, outerProps.target]);
  (0, _react.useEffect)(() => {
    if (!outerShow) {
      setFirstRenderedState(null);
    }
  }, [outerShow]);
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_Overlay.default, {
    ...outerProps,
    ref: mergedRef,
    popperConfig: {
      ...popperConfig,
      modifiers: modifiers.concat(popperConfig.modifiers || []),
      onFirstUpdate: handleFirstUpdate
    },
    transition: actualTransition,
    rootClose: rootClose,
    placement: placement,
    show: outerShow,
    children: (overlayProps, {
      arrowProps,
      popper: popperObj,
      show
    }) => {
      var _popperObj$state;
      wrapRefs(overlayProps, arrowProps);
      // Need to get placement from popper object, handling case when overlay is flipped using 'flip' prop
      const updatedPlacement = popperObj == null ? void 0 : popperObj.placement;
      const popper = Object.assign(popperRef.current, {
        state: popperObj == null ? void 0 : popperObj.state,
        scheduleUpdate: popperObj == null ? void 0 : popperObj.update,
        placement: updatedPlacement,
        outOfBoundaries: (popperObj == null || (_popperObj$state = popperObj.state) == null || (_popperObj$state = _popperObj$state.modifiersData.hide) == null ? void 0 : _popperObj$state.isReferenceHidden) || false,
        strategy: popperConfig.strategy
      });
      const hasDoneInitialMeasure = !!firstRenderedState;
      if (typeof overlay === 'function') return overlay({
        ...overlayProps,
        placement: updatedPlacement,
        show,
        ...(!transition && show && {
          className: 'show'
        }),
        popper,
        arrowProps,
        hasDoneInitialMeasure
      });
      return /*#__PURE__*/React.cloneElement(overlay, {
        ...overlayProps,
        placement: updatedPlacement,
        arrowProps,
        popper,
        hasDoneInitialMeasure,
        className: (0, _classnames.default)(overlay.props.className, !transition && show && 'show'),
        style: {
          ...overlay.props.style,
          ...overlayProps.style
        }
      });
    }
  });
});
Overlay.displayName = 'Overlay';
var _default = exports.default = Overlay;
module.exports = exports.default;