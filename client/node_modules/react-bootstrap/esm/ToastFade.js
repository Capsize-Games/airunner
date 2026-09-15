import * as React from 'react';
import { ENTERING, EXITING } from 'react-transition-group/Transition';
import Fade from './Fade';
import { jsx as _jsx } from "react/jsx-runtime";
const fadeStyles = {
  [ENTERING]: 'showing',
  [EXITING]: 'showing show'
};
const ToastFade = /*#__PURE__*/React.forwardRef((props, ref) => /*#__PURE__*/_jsx(Fade, {
  ...props,
  ref: ref,
  transitionClasses: fadeStyles
}));
ToastFade.displayName = 'ToastFade';
export default ToastFade;