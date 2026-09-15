"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useMemo } from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import FormCheckInput from './FormCheckInput';
import InputGroupContext from './InputGroupContext';
import InputGroupText from './InputGroupText';
import { jsx as _jsx } from "react/jsx-runtime";
const InputGroupCheckbox = props => /*#__PURE__*/_jsx(InputGroupText, {
  children: /*#__PURE__*/_jsx(FormCheckInput, {
    type: "checkbox",
    ...props
  })
});
const InputGroupRadio = props => /*#__PURE__*/_jsx(InputGroupText, {
  children: /*#__PURE__*/_jsx(FormCheckInput, {
    type: "radio",
    ...props
  })
});
const InputGroup = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  size,
  hasValidation,
  className,
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'div',
  ...props
}, ref) => {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'input-group');

  // Intentionally an empty object. Used in detecting if a dropdown
  // exists under an input group.
  const contextValue = useMemo(() => ({}), []);
  return /*#__PURE__*/_jsx(InputGroupContext.Provider, {
    value: contextValue,
    children: /*#__PURE__*/_jsx(Component, {
      ref: ref,
      ...props,
      className: classNames(className, bsPrefix, size && `${bsPrefix}-${size}`, hasValidation && 'has-validation')
    })
  });
});
InputGroup.displayName = 'InputGroup';
export default Object.assign(InputGroup, {
  Text: InputGroupText,
  Radio: InputGroupRadio,
  Checkbox: InputGroupCheckbox
});