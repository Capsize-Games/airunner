"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const ButtonToolbar = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  role = 'toolbar',
  ...props
}, ref) => {
  const prefix = useBootstrapPrefix(bsPrefix, 'btn-toolbar');
  return /*#__PURE__*/_jsx("div", {
    ...props,
    ref: ref,
    className: classNames(className, prefix),
    role: role
  });
});
ButtonToolbar.displayName = 'ButtonToolbar';
export default ButtonToolbar;