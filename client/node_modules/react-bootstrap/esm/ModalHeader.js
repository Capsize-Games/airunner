"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import AbstractModalHeader from './AbstractModalHeader';
import { jsx as _jsx } from "react/jsx-runtime";
const ModalHeader = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  closeLabel = 'Close',
  closeButton = false,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'modal-header');
  return /*#__PURE__*/_jsx(AbstractModalHeader, {
    ref: ref,
    ...props,
    className: classNames(className, bsPrefix),
    closeLabel: closeLabel,
    closeButton: closeButton
  });
});
ModalHeader.displayName = 'ModalHeader';
export default ModalHeader;