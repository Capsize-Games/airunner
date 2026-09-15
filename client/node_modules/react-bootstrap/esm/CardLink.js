"use client";

import * as React from 'react';
import classNames from 'classnames';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const CardLink = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = 'a',
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'card-link');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
CardLink.displayName = 'CardLink';
export default CardLink;