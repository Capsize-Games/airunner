"use client";

import * as React from 'react';
import { useContext } from 'react';
import Collapse from './Collapse';
import { useBootstrapPrefix } from './ThemeProvider';
import NavbarContext from './NavbarContext';
import { jsx as _jsx } from "react/jsx-runtime";
const NavbarCollapse = /*#__PURE__*/React.forwardRef(({
  children,
  bsPrefix,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'navbar-collapse');
  const context = useContext(NavbarContext);
  return /*#__PURE__*/_jsx(Collapse, {
    in: !!(context && context.expanded),
    ...props,
    children: /*#__PURE__*/_jsx("div", {
      ref: ref,
      className: bsPrefix,
      children: children
    })
  });
});
NavbarCollapse.displayName = 'NavbarCollapse';
export default NavbarCollapse;