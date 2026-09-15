"use client";

import * as React from 'react';
import classNames from 'classnames';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const InputGroupText = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = 'span',
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'input-group-text');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
InputGroupText.displayName = 'InputGroupText';
export default InputGroupText;