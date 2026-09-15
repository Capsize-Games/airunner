"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import AccordionButton from './AccordionButton';
import { jsx as _jsx } from "react/jsx-runtime";
const AccordionHeader = /*#__PURE__*/React.forwardRef(({
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'h2',
  'aria-controls': ariaControls,
  bsPrefix,
  className,
  children,
  onClick,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'accordion-header');
  return /*#__PURE__*/_jsx(Component, {
    ref: ref,
    ...props,
    className: classNames(className, bsPrefix),
    children: /*#__PURE__*/_jsx(AccordionButton, {
      onClick: onClick,
      "aria-controls": ariaControls,
      children: children
    })
  });
});
AccordionHeader.displayName = 'AccordionHeader';
export default AccordionHeader;