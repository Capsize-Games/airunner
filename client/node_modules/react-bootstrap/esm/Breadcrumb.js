"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import BreadcrumbItem from './BreadcrumbItem';
import { jsx as _jsx } from "react/jsx-runtime";
const Breadcrumb = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  listProps = {},
  children,
  label = 'breadcrumb',
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'nav',
  ...props
}, ref) => {
  const prefix = useBootstrapPrefix(bsPrefix, 'breadcrumb');
  return /*#__PURE__*/_jsx(Component, {
    "aria-label": label,
    className: className,
    ref: ref,
    ...props,
    children: /*#__PURE__*/_jsx("ol", {
      ...listProps,
      className: classNames(prefix, listProps == null ? void 0 : listProps.className),
      children: children
    })
  });
});
Breadcrumb.displayName = 'Breadcrumb';
export default Object.assign(Breadcrumb, {
  Item: BreadcrumbItem
});