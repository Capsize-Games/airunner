"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useMemo } from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import AccordionItemContext from './AccordionItemContext';
import { jsx as _jsx } from "react/jsx-runtime";
const AccordionItem = /*#__PURE__*/React.forwardRef(({
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'div',
  bsPrefix,
  className,
  eventKey,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'accordion-item');
  const contextValue = useMemo(() => ({
    eventKey
  }), [eventKey]);
  return /*#__PURE__*/_jsx(AccordionItemContext.Provider, {
    value: contextValue,
    children: /*#__PURE__*/_jsx(Component, {
      ref: ref,
      ...props,
      className: classNames(className, bsPrefix)
    })
  });
});
AccordionItem.displayName = 'AccordionItem';
export default AccordionItem;