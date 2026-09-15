"use client";

import * as React from 'react';
import { useEffect, useMemo, useRef, useCallback } from 'react';
import classNames from 'classnames';
import useTimeout from '@restart/hooks/useTimeout';
import ToastFade from './ToastFade';
import ToastHeader from './ToastHeader';
import ToastBody from './ToastBody';
import { useBootstrapPrefix } from './ThemeProvider';
import ToastContext from './ToastContext';
import { jsx as _jsx } from "react/jsx-runtime";
const Toast = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  transition: Transition = ToastFade,
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
  bsPrefix = useBootstrapPrefix(bsPrefix, 'toast');

  // We use refs for these, because we don't want to restart the autohide
  // timer in case these values change.
  const delayRef = useRef(delay);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    delayRef.current = delay;
    onCloseRef.current = onClose;
  }, [delay, onClose]);
  const autohideTimeout = useTimeout();
  const autohideToast = !!(autohide && show);
  const autohideFunc = useCallback(() => {
    if (autohideToast) {
      onCloseRef.current == null || onCloseRef.current();
    }
  }, [autohideToast]);
  useEffect(() => {
    // Only reset timer if show or autohide changes.
    autohideTimeout.set(autohideFunc, delayRef.current);
  }, [autohideTimeout, autohideFunc]);
  const toastContext = useMemo(() => ({
    onClose
  }), [onClose]);
  const hasAnimation = !!(Transition && animation);
  const toast = /*#__PURE__*/_jsx("div", {
    ...props,
    ref: ref,
    className: classNames(bsPrefix, className, bg && `bg-${bg}`, !hasAnimation && (show ? 'show' : 'hide')),
    role: "alert",
    "aria-live": "assertive",
    "aria-atomic": "true"
  });
  return /*#__PURE__*/_jsx(ToastContext.Provider, {
    value: toastContext,
    children: hasAnimation && Transition ? /*#__PURE__*/_jsx(Transition, {
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
export default Object.assign(Toast, {
  Body: ToastBody,
  Header: ToastHeader
});