"use client";

import classNames from 'classnames';
import * as React from 'react';
import { useContext } from 'react';
import { useBootstrapPrefix } from './ThemeProvider';
import FormContext from './FormContext';
import { jsx as _jsx } from "react/jsx-runtime";
const FormRange = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  id,
  ...props
}, ref) => {
  const {
    controlId
  } = useContext(FormContext);
  bsPrefix = useBootstrapPrefix(bsPrefix, 'form-range');
  return /*#__PURE__*/_jsx("input", {
    ...props,
    type: "range",
    ref: ref,
    className: classNames(className, bsPrefix),
    id: id || controlId
  });
});
FormRange.displayName = 'FormRange';
export default FormRange;