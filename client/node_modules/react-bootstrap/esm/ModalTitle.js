"use client";

import * as React from 'react';
import classNames from 'classnames';
import divWithClassName from './divWithClassName';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const DivStyledAsH4 = divWithClassName('h4');
const ModalTitle = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = DivStyledAsH4,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'modal-title');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
ModalTitle.displayName = 'ModalTitle';
export default ModalTitle;