"use client";

import * as React from 'react';
import { useContext } from 'react';
import useEventCallback from '@restart/hooks/useEventCallback';
import Offcanvas from './Offcanvas';
import NavbarContext from './NavbarContext';
import { jsx as _jsx } from "react/jsx-runtime";
const NavbarOffcanvas = /*#__PURE__*/React.forwardRef(({
  onHide,
  ...props
}, ref) => {
  const context = useContext(NavbarContext);
  const handleHide = useEventCallback(() => {
    context == null || context.onToggle == null || context.onToggle();
    onHide == null || onHide();
  });
  return /*#__PURE__*/_jsx(Offcanvas, {
    ref: ref,
    show: !!(context != null && context.expanded),
    ...props,
    renderStaticNode: true,
    onHide: handleHide
  });
});
NavbarOffcanvas.displayName = 'NavbarOffcanvas';
export default NavbarOffcanvas;