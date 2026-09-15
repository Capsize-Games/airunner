"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useContext } from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import Collapse from './Collapse';
import AccordionContext, { isAccordionItemSelected } from './AccordionContext';
import { jsx as _jsx } from "react/jsx-runtime";
/**
 * This component accepts all of [`Collapse`'s props](/docs/utilities/transitions#collapse-1).
 */
const AccordionCollapse = /*#__PURE__*/React.forwardRef(({
  as: Component = 'div',
  bsPrefix,
  className,
  children,
  eventKey,
  ...props
}, ref) => {
  const {
    activeEventKey
  } = useContext(AccordionContext);
  bsPrefix = useBootstrapPrefix(bsPrefix, 'accordion-collapse');
  return /*#__PURE__*/_jsx(Collapse, {
    ref: ref,
    in: isAccordionItemSelected(activeEventKey, eventKey),
    ...props,
    className: classNames(className, bsPrefix),
    children: /*#__PURE__*/_jsx(Component, {
      children: React.Children.only(children)
    })
  });
});
AccordionCollapse.displayName = 'AccordionCollapse';
export default AccordionCollapse;