"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
function toPercent(num) {
  if (num <= 0) return '100%';
  if (num < 1) return `${num * 100}%`;
  return `${num}%`;
}
const Ratio = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  children,
  aspectRatio = '1x1',
  style,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'ratio');
  const isCustomRatio = typeof aspectRatio === 'number';
  return /*#__PURE__*/_jsx("div", {
    ref: ref,
    ...props,
    style: {
      ...style,
      ...(isCustomRatio && {
        '--bs-aspect-ratio': toPercent(aspectRatio)
      })
    },
    className: classNames(bsPrefix, className, !isCustomRatio && `${bsPrefix}-${aspectRatio}`),
    children: React.Children.only(children)
  });
});
Ratio.displayName = 'Ratio';
export default Ratio;