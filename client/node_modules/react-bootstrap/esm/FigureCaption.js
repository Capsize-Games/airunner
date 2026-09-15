"use client";

import * as React from 'react';
import classNames from 'classnames';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const FigureCaption = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = 'figcaption',
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'figure-caption');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
FigureCaption.displayName = 'FigureCaption';
export default FigureCaption;