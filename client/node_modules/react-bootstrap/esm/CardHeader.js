"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useMemo } from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import CardHeaderContext from './CardHeaderContext';
import { jsx as _jsx } from "react/jsx-runtime";
const CardHeader = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'div',
  ...props
}, ref) => {
  const prefix = useBootstrapPrefix(bsPrefix, 'card-header');
  const contextValue = useMemo(() => ({
    cardHeaderBsPrefix: prefix
  }), [prefix]);
  return /*#__PURE__*/_jsx(CardHeaderContext.Provider, {
    value: contextValue,
    children: /*#__PURE__*/_jsx(Component, {
      ref: ref,
      ...props,
      className: classNames(className, prefix)
    })
  });
});
CardHeader.displayName = 'CardHeader';
export default CardHeader;