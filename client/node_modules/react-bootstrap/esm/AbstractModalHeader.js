"use client";

import * as React from 'react';
import { useContext } from 'react';
import useEventCallback from '@restart/hooks/useEventCallback';
import CloseButton from './CloseButton';
import ModalContext from './ModalContext';
import { jsx as _jsx } from "react/jsx-runtime";
import { jsxs as _jsxs } from "react/jsx-runtime";
const AbstractModalHeader = /*#__PURE__*/React.forwardRef(({
  closeLabel = 'Close',
  closeVariant,
  closeButton = false,
  onHide,
  children,
  ...props
}, ref) => {
  const context = useContext(ModalContext);
  const handleClick = useEventCallback(() => {
    context == null || context.onHide();
    onHide == null || onHide();
  });
  return /*#__PURE__*/_jsxs("div", {
    ref: ref,
    ...props,
    children: [children, closeButton && /*#__PURE__*/_jsx(CloseButton, {
      "aria-label": closeLabel,
      variant: closeVariant,
      onClick: handleClick
    })]
  });
});
AbstractModalHeader.displayName = 'AbstractModalHeader';
export default AbstractModalHeader;