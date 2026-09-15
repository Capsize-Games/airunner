import * as React from 'react';
import FormCheck from './FormCheck';
import { jsx as _jsx } from "react/jsx-runtime";
const Switch = /*#__PURE__*/React.forwardRef((props, ref) => /*#__PURE__*/_jsx(FormCheck, {
  ...props,
  ref: ref,
  type: "switch"
}));
Switch.displayName = 'Switch';
export default Object.assign(Switch, {
  Input: FormCheck.Input,
  Label: FormCheck.Label
});