"use client";

import * as React from 'react';
import classNames from 'classnames';
import { useBootstrapPrefix } from './ThemeProvider';
import divWithClassName from './divWithClassName';
import { jsx as _jsx } from "react/jsx-runtime";
const DivStyledAsH6 = divWithClassName('h6');
const CardSubtitle = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = DivStyledAsH6,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'card-subtitle');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
CardSubtitle.displayName = 'CardSubtitle';
export default CardSubtitle;