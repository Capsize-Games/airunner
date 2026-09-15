"use client";

import classNames from 'classnames';
import useBreakpoint from '@restart/hooks/useBreakpoint';
import useEventCallback from '@restart/hooks/useEventCallback';
import * as React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import BaseModal from '@restart/ui/Modal';
import Fade from './Fade';
import OffcanvasBody from './OffcanvasBody';
import OffcanvasToggling from './OffcanvasToggling';
import ModalContext from './ModalContext';
import OffcanvasHeader from './OffcanvasHeader';
import OffcanvasTitle from './OffcanvasTitle';
import { useBootstrapPrefix } from './ThemeProvider';
import BootstrapModalManager, { getSharedManager } from './BootstrapModalManager';
import { jsx as _jsx } from "react/jsx-runtime";
import { Fragment as _Fragment } from "react/jsx-runtime";
import { jsxs as _jsxs } from "react/jsx-runtime";
function DialogTransition(props) {
  return /*#__PURE__*/_jsx(OffcanvasToggling, {
    ...props
  });
}
function BackdropTransition(props) {
  return /*#__PURE__*/_jsx(Fade, {
    ...props
  });
}
const Offcanvas = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  children,
  'aria-labelledby': ariaLabelledby,
  placement = 'start',
  responsive,
  /* BaseModal props */

  show = false,
  backdrop = true,
  keyboard = true,
  scroll = false,
  onEscapeKeyDown,
  onShow,
  onHide,
  container,
  autoFocus = true,
  enforceFocus = true,
  restoreFocus = true,
  restoreFocusOptions,
  onEntered,
  onExit,
  onExiting,
  onEnter,
  onEntering,
  onExited,
  backdropClassName,
  manager: propsManager,
  renderStaticNode = false,
  ...props
}, ref) => {
  const modalManager = useRef();
  bsPrefix = useBootstrapPrefix(bsPrefix, 'offcanvas');
  const [showOffcanvas, setShowOffcanvas] = useState(false);
  const handleHide = useEventCallback(onHide);
  const hideResponsiveOffcanvas = useBreakpoint(responsive || 'xs', 'up');
  useEffect(() => {
    // Handles the case where screen is resized while the responsive
    // offcanvas is shown. If `responsive` not provided, just use `show`.
    setShowOffcanvas(responsive ? show && !hideResponsiveOffcanvas : show);
  }, [show, responsive, hideResponsiveOffcanvas]);
  const modalContext = useMemo(() => ({
    onHide: handleHide
  }), [handleHide]);
  function getModalManager() {
    if (propsManager) return propsManager;
    if (scroll) {
      // Have to use a different modal manager since the shared
      // one handles overflow.
      if (!modalManager.current) modalManager.current = new BootstrapModalManager({
        handleContainerOverflow: false
      });
      return modalManager.current;
    }
    return getSharedManager();
  }
  const handleEnter = (node, ...args) => {
    if (node) node.style.visibility = 'visible';
    onEnter == null || onEnter(node, ...args);
  };
  const handleExited = (node, ...args) => {
    if (node) node.style.visibility = '';
    onExited == null || onExited(...args);
  };
  const renderBackdrop = useCallback(backdropProps => /*#__PURE__*/_jsx("div", {
    ...backdropProps,
    className: classNames(`${bsPrefix}-backdrop`, backdropClassName)
  }), [backdropClassName, bsPrefix]);
  const renderDialog = dialogProps => /*#__PURE__*/_jsx("div", {
    ...dialogProps,
    ...props,
    className: classNames(className, responsive ? `${bsPrefix}-${responsive}` : bsPrefix, `${bsPrefix}-${placement}`),
    "aria-labelledby": ariaLabelledby,
    children: children
  });
  return /*#__PURE__*/_jsxs(_Fragment, {
    children: [!showOffcanvas && (responsive || renderStaticNode) && renderDialog({}), /*#__PURE__*/_jsx(ModalContext.Provider, {
      value: modalContext,
      children: /*#__PURE__*/_jsx(BaseModal, {
        show: showOffcanvas,
        ref: ref,
        backdrop: backdrop,
        container: container,
        keyboard: keyboard,
        autoFocus: autoFocus,
        enforceFocus: enforceFocus && !scroll,
        restoreFocus: restoreFocus,
        restoreFocusOptions: restoreFocusOptions,
        onEscapeKeyDown: onEscapeKeyDown,
        onShow: onShow,
        onHide: handleHide,
        onEnter: handleEnter,
        onEntering: onEntering,
        onEntered: onEntered,
        onExit: onExit,
        onExiting: onExiting,
        onExited: handleExited,
        manager: getModalManager(),
        transition: DialogTransition,
        backdropTransition: BackdropTransition,
        renderBackdrop: renderBackdrop,
        renderDialog: renderDialog
      })
    })]
  });
});
Offcanvas.displayName = 'Offcanvas';
export default Object.assign(Offcanvas, {
  Body: OffcanvasBody,
  Header: OffcanvasHeader,
  Title: OffcanvasTitle
});