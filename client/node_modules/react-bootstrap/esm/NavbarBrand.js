"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const NavbarBrand = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  as,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'navbar-brand');
  const Component = as || (props.href ? 'a' : 'span');
  return /*#__PURE__*/_jsx(Component, {
    ...props,
    ref: ref,
    className: classNames(className, bsPrefix)
  });
});
NavbarBrand.displayName = 'NavbarBrand';
export default NavbarBrand;