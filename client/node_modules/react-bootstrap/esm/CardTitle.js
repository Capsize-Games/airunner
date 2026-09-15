"use client";

import * as React from 'react';
import classNames from 'classnames';
import { useBootstrapPrefix } from './ThemeProvider';
import divWithClassName from './divWithClassName';
import { jsx as _jsx } from "react/jsx-runtime";
const DivStyledAsH5 = divWithClassName('h5');
const CardTitle = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = DivStyledAsH5,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'card-title');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
CardTitle.displayName = 'CardTitle';
export default CardTitle;