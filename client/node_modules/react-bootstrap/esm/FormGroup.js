import * as React from 'react';
import { useMemo } from 'react';
import FormContext from './FormContext';
import { jsx as _jsx } from "react/jsx-runtime";
const FormGroup = /*#__PURE__*/React.forwardRef(({
  controlId,
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'div',
  ...props
}, ref) => {
  const context = useMemo(() => ({
    controlId
  }), [controlId]);
  return /*#__PURE__*/_jsx(FormContext.Provider, {
    value: context,
    children: /*#__PURE__*/_jsx(Component, {
      ...props,
      ref: ref
    })
  });
});
FormGroup.displayName = 'FormGroup';
export default FormGroup;