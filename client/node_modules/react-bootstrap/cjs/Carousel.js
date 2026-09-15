"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _useEventCallback = _interopRequireDefault(require("@restart/hooks/useEventCallback"));
var _useUpdateEffect = _interopRequireDefault(require("@restart/hooks/useUpdateEffect"));
var _useCommittedRef = _interopRequireDefault(require("@restart/hooks/useCommittedRef"));
var _useTimeout = _interopRequireDefault(require("@restart/hooks/useTimeout"));
var _Anchor = _interopRequireDefault(require("@restart/ui/Anchor"));
var _classnames = _interopRequireDefault(require("classnames"));
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _uncontrollable = require("uncontrollable");
var _CarouselCaption = _interopRequireDefault(require("./CarouselCaption"));
var _CarouselItem = _interopRequireDefault(require("./CarouselItem"));
var _ElementChildren = require("./ElementChildren");
var _ThemeProvider = require("./ThemeProvider");
var _transitionEndListener = _interopRequireDefault(require("./transitionEndListener"));
var _triggerBrowserReflow = _interopRequireDefault(require("./triggerBrowserReflow"));
var _TransitionWrapper = _interopRequireDefault(require("./TransitionWrapper"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const SWIPE_THRESHOLD = 40;
function isVisible(element) {
  if (!element || !element.style || !element.parentNode || !element.parentNode.style) {
    return false;
  }
  const elementStyle = getComputedStyle(element);
  return elementStyle.display !== 'none' && elementStyle.visibility !== 'hidden' && getComputedStyle(element.parentNode).display !== 'none';
}
const Carousel =
/*#__PURE__*/
// eslint-disable-next-line react/display-name
React.forwardRef(({
  defaultActiveIndex = 0,
  ...uncontrolledProps
}, ref) => {
  const {
    // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
    as: Component = 'div',
    bsPrefix,
    slide = true,
    fade = false,
    controls = true,
    indicators = true,
    indicatorLabels = [],
    activeIndex,
    onSelect,
    onSlide,
    onSlid,
    interval = 5000,
    keyboard = true,
    onKeyDown,
    pause = 'hover',
    onMouseOver,
    onMouseOut,
    wrap = true,
    touch = true,
    onTouchStart,
    onTouchMove,
    onTouchEnd,
    prevIcon = /*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
      "aria-hidden": "true",
      className: "carousel-control-prev-icon"
    }),
    prevLabel = 'Previous',
    nextIcon = /*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
      "aria-hidden": "true",
      className: "carousel-control-next-icon"
    }),
    nextLabel = 'Next',
    variant,
    className,
    children,
    ...props
  } = (0, _uncontrollable.useUncontrolled)({
    defaultActiveIndex,
    ...uncontrolledProps
  }, {
    activeIndex: 'onSelect'
  });
  const prefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'carousel');
  const isRTL = (0, _ThemeProvider.useIsRTL)();
  const nextDirectionRef = (0, _react.useRef)(null);
  const [direction, setDirection] = (0, _react.useState)('next');
  const [paused, setPaused] = (0, _react.useState)(false);
  const [isSliding, setIsSliding] = (0, _react.useState)(false);
  const [renderedActiveIndex, setRenderedActiveIndex] = (0, _react.useState)(activeIndex || 0);
  (0, _react.useEffect)(() => {
    if (!isSliding && activeIndex !== renderedActiveIndex) {
      if (nextDirectionRef.current) {
        setDirection(nextDirectionRef.current);
      } else {
        setDirection((activeIndex || 0) > renderedActiveIndex ? 'next' : 'prev');
      }
      if (slide) {
        setIsSliding(true);
      }
      setRenderedActiveIndex(activeIndex || 0);
    }
  }, [activeIndex, isSliding, renderedActiveIndex, slide]);
  (0, _react.useEffect)(() => {
    if (nextDirectionRef.current) {
      nextDirectionRef.current = null;
    }
  });
  let numChildren = 0;
  let activeChildInterval;

  // Iterate to grab all of the children's interval values
  // (and count them, too)
  (0, _ElementChildren.forEach)(children, (child, index) => {
    ++numChildren;
    if (index === activeIndex) {
      activeChildInterval = child.props.interval;
    }
  });
  const activeChildIntervalRef = (0, _useCommittedRef.default)(activeChildInterval);
  const prev = (0, _react.useCallback)(event => {
    if (isSliding) {
      return;
    }
    let nextActiveIndex = renderedActiveIndex - 1;
    if (nextActiveIndex < 0) {
      if (!wrap) {
        return;
      }
      nextActiveIndex = numChildren - 1;
    }
    nextDirectionRef.current = 'prev';
    onSelect == null || onSelect(nextActiveIndex, event);
  }, [isSliding, renderedActiveIndex, onSelect, wrap, numChildren]);

  // This is used in the setInterval, so it should not invalidate.
  const next = (0, _useEventCallback.default)(event => {
    if (isSliding) {
      return;
    }
    let nextActiveIndex = renderedActiveIndex + 1;
    if (nextActiveIndex >= numChildren) {
      if (!wrap) {
        return;
      }
      nextActiveIndex = 0;
    }
    nextDirectionRef.current = 'next';
    onSelect == null || onSelect(nextActiveIndex, event);
  });
  const elementRef = (0, _react.useRef)();
  (0, _react.useImperativeHandle)(ref, () => ({
    element: elementRef.current,
    prev,
    next
  }));

  // This is used in the setInterval, so it should not invalidate.
  const nextWhenVisible = (0, _useEventCallback.default)(() => {
    if (!document.hidden && isVisible(elementRef.current)) {
      if (isRTL) {
        prev();
      } else {
        next();
      }
    }
  });
  const slideDirection = direction === 'next' ? 'start' : 'end';
  (0, _useUpdateEffect.default)(() => {
    if (slide) {
      // These callbacks will be handled by the <Transition> callbacks.
      return;
    }
    onSlide == null || onSlide(renderedActiveIndex, slideDirection);
    onSlid == null || onSlid(renderedActiveIndex, slideDirection);
  }, [renderedActiveIndex]);
  const orderClassName = `${prefix}-item-${direction}`;
  const directionalClassName = `${prefix}-item-${slideDirection}`;
  const handleEnter = (0, _react.useCallback)(node => {
    (0, _triggerBrowserReflow.default)(node);
    onSlide == null || onSlide(renderedActiveIndex, slideDirection);
  }, [onSlide, renderedActiveIndex, slideDirection]);
  const handleEntered = (0, _react.useCallback)(() => {
    setIsSliding(false);
    onSlid == null || onSlid(renderedActiveIndex, slideDirection);
  }, [onSlid, renderedActiveIndex, slideDirection]);
  const handleKeyDown = (0, _react.useCallback)(event => {
    if (keyboard && !/input|textarea/i.test(event.target.tagName)) {
      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          if (isRTL) {
            next(event);
          } else {
            prev(event);
          }
          return;
        case 'ArrowRight':
          event.preventDefault();
          if (isRTL) {
            prev(event);
          } else {
            next(event);
          }
          return;
        default:
      }
    }
    onKeyDown == null || onKeyDown(event);
  }, [keyboard, onKeyDown, prev, next, isRTL]);
  const handleMouseOver = (0, _react.useCallback)(event => {
    if (pause === 'hover') {
      setPaused(true);
    }
    onMouseOver == null || onMouseOver(event);
  }, [pause, onMouseOver]);
  const handleMouseOut = (0, _react.useCallback)(event => {
    setPaused(false);
    onMouseOut == null || onMouseOut(event);
  }, [onMouseOut]);
  const touchStartXRef = (0, _react.useRef)(0);
  const touchDeltaXRef = (0, _react.useRef)(0);
  const touchUnpauseTimeout = (0, _useTimeout.default)();
  const handleTouchStart = (0, _react.useCallback)(event => {
    touchStartXRef.current = event.touches[0].clientX;
    touchDeltaXRef.current = 0;
    if (pause === 'hover') {
      setPaused(true);
    }
    onTouchStart == null || onTouchStart(event);
  }, [pause, onTouchStart]);
  const handleTouchMove = (0, _react.useCallback)(event => {
    if (event.touches && event.touches.length > 1) {
      touchDeltaXRef.current = 0;
    } else {
      touchDeltaXRef.current = event.touches[0].clientX - touchStartXRef.current;
    }
    onTouchMove == null || onTouchMove(event);
  }, [onTouchMove]);
  const handleTouchEnd = (0, _react.useCallback)(event => {
    if (touch) {
      const touchDeltaX = touchDeltaXRef.current;
      if (Math.abs(touchDeltaX) > SWIPE_THRESHOLD) {
        if (touchDeltaX > 0) {
          prev(event);
        } else {
          next(event);
        }
      }
    }
    if (pause === 'hover') {
      touchUnpauseTimeout.set(() => {
        setPaused(false);
      }, interval || undefined);
    }
    onTouchEnd == null || onTouchEnd(event);
  }, [touch, pause, prev, next, touchUnpauseTimeout, interval, onTouchEnd]);
  const shouldPlay = interval != null && !paused && !isSliding;
  const intervalHandleRef = (0, _react.useRef)();
  (0, _react.useEffect)(() => {
    var _ref, _activeChildIntervalR;
    if (!shouldPlay) {
      return undefined;
    }
    const nextFunc = isRTL ? prev : next;
    intervalHandleRef.current = window.setInterval(document.visibilityState ? nextWhenVisible : nextFunc, (_ref = (_activeChildIntervalR = activeChildIntervalRef.current) != null ? _activeChildIntervalR : interval) != null ? _ref : undefined);
    return () => {
      if (intervalHandleRef.current !== null) {
        clearInterval(intervalHandleRef.current);
      }
    };
  }, [shouldPlay, prev, next, activeChildIntervalRef, interval, nextWhenVisible, isRTL]);
  const indicatorOnClicks = (0, _react.useMemo)(() => indicators && Array.from({
    length: numChildren
  }, (_, index) => event => {
    onSelect == null || onSelect(index, event);
  }), [indicators, numChildren, onSelect]);
  return /*#__PURE__*/(0, _jsxRuntime.jsxs)(Component, {
    ref: elementRef,
    ...props,
    onKeyDown: handleKeyDown,
    onMouseOver: handleMouseOver,
    onMouseOut: handleMouseOut,
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
    className: (0, _classnames.default)(className, prefix, slide && 'slide', fade && `${prefix}-fade`, variant && `${prefix}-${variant}`),
    children: [indicators && /*#__PURE__*/(0, _jsxRuntime.jsx)("div", {
      className: `${prefix}-indicators`,
      children: (0, _ElementChildren.map)(children, (_, index) => /*#__PURE__*/(0, _jsxRuntime.jsx)("button", {
        type: "button",
        "data-bs-target": "" // Bootstrap requires this in their css.
        ,
        "aria-label": indicatorLabels != null && indicatorLabels.length ? indicatorLabels[index] : `Slide ${index + 1}`,
        className: index === renderedActiveIndex ? 'active' : undefined,
        onClick: indicatorOnClicks ? indicatorOnClicks[index] : undefined,
        "aria-current": index === renderedActiveIndex
      }, index))
    }), /*#__PURE__*/(0, _jsxRuntime.jsx)("div", {
      className: `${prefix}-inner`,
      children: (0, _ElementChildren.map)(children, (child, index) => {
        const isActive = index === renderedActiveIndex;
        return slide ? /*#__PURE__*/(0, _jsxRuntime.jsx)(_TransitionWrapper.default, {
          in: isActive,
          onEnter: isActive ? handleEnter : undefined,
          onEntered: isActive ? handleEntered : undefined,
          addEndListener: _transitionEndListener.default,
          children: (status, innerProps) => /*#__PURE__*/React.cloneElement(child, {
            ...innerProps,
            className: (0, _classnames.default)(child.props.className, isActive && status !== 'entered' && orderClassName, (status === 'entered' || status === 'exiting') && 'active', (status === 'entering' || status === 'exiting') && directionalClassName)
          })
        }) : ( /*#__PURE__*/React.cloneElement(child, {
          className: (0, _classnames.default)(child.props.className, isActive && 'active')
        }));
      })
    }), controls && /*#__PURE__*/(0, _jsxRuntime.jsxs)(_jsxRuntime.Fragment, {
      children: [(wrap || activeIndex !== 0) && /*#__PURE__*/(0, _jsxRuntime.jsxs)(_Anchor.default, {
        className: `${prefix}-control-prev`,
        onClick: prev,
        children: [prevIcon, prevLabel && /*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
          className: "visually-hidden",
          children: prevLabel
        })]
      }), (wrap || activeIndex !== numChildren - 1) && /*#__PURE__*/(0, _jsxRuntime.jsxs)(_Anchor.default, {
        className: `${prefix}-control-next`,
        onClick: next,
        children: [nextIcon, nextLabel && /*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
          className: "visually-hidden",
          children: nextLabel
        })]
      })]
    })]
  });
});
Carousel.displayName = 'Carousel';
var _default = exports.default = Object.assign(Carousel, {
  Caption: _CarouselCaption.default,
  Item: _CarouselItem.default
});
module.exports = exports.default;