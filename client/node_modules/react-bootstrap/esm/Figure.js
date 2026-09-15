"use client";

import * as React from 'react';
import classNames from 'classnames';
import FigureImage from './FigureImage';
import FigureCaption from './FigureCaption';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const Figure = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = 'figure',
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'figure');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
Figure.displayName = 'Figure';
export default Object.assign(Figure, {
  Image: FigureImage,
  Caption: FigureCaption
});