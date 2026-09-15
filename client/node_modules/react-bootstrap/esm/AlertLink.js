"use client";

import * as React from 'react';
import classNames from 'classnames';
import Anchor from '@restart/ui/Anchor';
import { useBootstrapPrefix } from './ThemeProvider';
import { jsx as _jsx } from "react/jsx-runtime";
const AlertLink = /*#__PURE__*/React.forwardRef(({
  className,
  bsPrefix,
  as: Component = Anchor,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'alert-link');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    className: classNames(className, bsPrefix),
    ...props
  });
});
AlertLink.displayName = 'AlertLink';
export default AlertLink;