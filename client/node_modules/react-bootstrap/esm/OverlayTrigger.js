"use client";

import contains from 'dom-helpers/contains';
import PropTypes from 'prop-types';
import * as React from 'react';
import { cloneElement, useCallback, useRef } from 'react';
import useTimeout from '@restart/hooks/useTimeout';
import warning from 'warning';
import { useUncontrolledProp } from 'uncontrollable';
import useMergedRefs from '@restart/hooks/useMergedRefs';
import { getChildRef } from '@restart/ui/utils';
import Overlay from './Overlay';
import safeFindDOMNode from './safeFindDOMNode';
import { jsx as _jsx } from "react/jsx-runtime";
import { Fragment as _Fragment } from "react/jsx-runtime";
import { jsxs as _jsxs } from "react/jsx-runtime";
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
  if ((!related || related !== target) && !contains(target, related)) {
    handler(...args);
  }
}
const triggerType = PropTypes.oneOf(['click', 'hover', 'focus']);
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
  const triggerNodeRef = useRef(null);
  const mergedRef = useMergedRefs(triggerNodeRef, getChildRef(children));
  const timeout = useTimeout();
  const hoverStateRef = useRef('');
  const [show, setShow] = useUncontrolledProp(propsShow, defaultShow, onToggle);
  const delay = normalizeDelay(propsDelay);
  const {
    onFocus,
    onBlur,
    onClick
  } = typeof children !== 'function' ? React.Children.only(children).props : {};
  const attachRef = r => {
    mergedRef(safeFindDOMNode(r));
  };
  const handleShow = useCallback(() => {
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
  const handleHide = useCallback(() => {
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
  const handleFocus = useCallback((...args) => {
    handleShow();
    onFocus == null || onFocus(...args);
  }, [handleShow, onFocus]);
  const handleBlur = useCallback((...args) => {
    handleHide();
    onBlur == null || onBlur(...args);
  }, [handleHide, onBlur]);
  const handleClick = useCallback((...args) => {
    setShow(!show);
    onClick == null || onClick(...args);
  }, [onClick, setShow, show]);
  const handleMouseOver = useCallback((...args) => {
    handleMouseOverOut(handleShow, args, 'fromElement');
  }, [handleShow]);
  const handleMouseOut = useCallback((...args) => {
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
    process.env.NODE_ENV !== "production" ? warning(triggers.length > 1, '[react-bootstrap] Specifying only the `"hover"` trigger limits the visibility of the overlay to just mouse users. Consider also including the `"focus"` trigger so that touch and keyboard only users can see the overlay as well.') : void 0;
    triggerProps.onMouseOver = handleMouseOver;
    triggerProps.onMouseOut = handleMouseOut;
  }
  return /*#__PURE__*/_jsxs(_Fragment, {
    children: [typeof children === 'function' ? children(triggerProps) : /*#__PURE__*/cloneElement(children, triggerProps), /*#__PURE__*/_jsx(Overlay, {
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
export default OverlayTrigger;