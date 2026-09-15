"use client";

import * as React from 'react';
import classNames from 'classnames';
import divWithClassName from './divWithClassName';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const DivStyledAsH5 = divWithClassName('h5');
const OffcanvasTitle = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = DivStyledAsH5,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'offcanvas-title');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
OffcanvasTitle.displayName = 'OffcanvasTitle';
export default OffcanvasTitle;