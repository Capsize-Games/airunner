"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useContext } from 'react';
import useEventCallback from '@restart/hooks/useEventCallback';
import { useBootstrapPrefix } from './ThemeProvider';
import NavbarContext from './NavbarContext';
import { jsx as _jsx } from "react/jsx-runtime";
const NavbarToggle = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  children,
  label = 'Toggle navigation',
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'button',
  onClick,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'navbar-toggler');
  const {
    onToggle,
    expanded
  } = useContext(NavbarContext) || {};
  const handleClick = useEventCallback(e => {
    if (onClick) onClick(e);
    if (onToggle) onToggle();
  });
  if (Component === 'button') {
    props.type = 'button';
  }
  return /*#__PURE__*/_jsx(Component, {
    ...props,
    ref: ref,
    onClick: handleClick,
    "aria-label": label,
    className: classNames(className, bsPrefix, !expanded && 'collapsed'),
    children: children || /*#__PURE__*/_jsx("span", {
      className: `${bsPrefix}-icon`
    })
  });
});
NavbarToggle.displayName = 'NavbarToggle';
export default NavbarToggle;