"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import Button from './Button';
import { jsx as _jsx } from "react/jsx-runtime";
import { Fragment as _Fragment } from "react/jsx-runtime";
import { jsxs as _jsxs } from "react/jsx-runtime";
const noop = () => undefined;
const ToggleButton = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  name,
  className,
  checked,
  type,
  onChange,
  value,
  disabled,
  id,
  inputRef,
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'btn-check');
  return /*#__PURE__*/_jsxs(_Fragment, {
    children: [/*#__PURE__*/_jsx("input", {
      className: bsPrefix,
      name: name,
      type: type,
      value: value,
      ref: inputRef,
      autoComplete: "off",
      checked: !!checked,
      disabled: !!disabled,
      onChange: onChange || noop,
      id: id
    }), /*#__PURE__*/_jsx(Button, {
      ...props,
      ref: ref,
      className: classNames(className, disabled && 'disabled'),
      type: undefined,
      role: undefined,
      as: "label",
      htmlFor: id
    })]
  });
});
ToggleButton.displayName = 'ToggleButton';
export default ToggleButton;