"use client";

import classNames from 'classnames';
import * as React from 'react';
import warning from 'warning';
import { useUncontrolled } from 'uncontrollable';
import BaseNav from '@restart/ui/Nav';
import { useBootstrapPrefix } from './ThemeProvider';
import ListGroupItem from './ListGroupItem';
import { jsx as _jsx } from "react/jsx-runtime";
const ListGroup = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    className,
    bsPrefix: initialBsPrefix,
    variant,
    horizontal,
    numbered,
    // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
    as = 'div',
    ...controlledProps
  } = useUncontrolled(props, {
    activeKey: 'onSelect'
  });
  const bsPrefix = useBootstrapPrefix(initialBsPrefix, 'list-group');
  let horizontalVariant;
  if (horizontal) {
    horizontalVariant = horizontal === true ? 'horizontal' : `horizontal-${horizontal}`;
  }
  process.env.NODE_ENV !== "production" ? warning(!(horizontal && variant === 'flush'), '`variant="flush"` and `horizontal` should not be used together.') : void 0;
  return /*#__PURE__*/_jsx(BaseNav, {
    ref: ref,
    ...controlledProps,
    as: as,
    className: classNames(className, bsPrefix, variant && `${bsPrefix}-${variant}`, horizontalVariant && `${bsPrefix}-${horizontalVariant}`, numbered && `${bsPrefix}-numbered`)
  });
});
ListGroup.displayName = 'ListGroup';
export default Object.assign(ListGroup, {
  Item: ListGroupItem
});