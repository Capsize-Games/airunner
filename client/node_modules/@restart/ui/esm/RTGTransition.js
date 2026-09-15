const _excluded = ["component"];
function _objectWithoutPropertiesLoose(r, e) { if (null == r) return {}; var t = {}; for (var n in r) if ({}.hasOwnProperty.call(r, n)) { if (e.indexOf(n) >= 0) continue; t[n] = r[n]; } return t; }
import * as React from 'react';
import useRTGTransitionProps from './useRTGTransitionProps';
import { jsx as _jsx } from "react/jsx-runtime";
// Normalizes Transition callbacks when nodeRef is used.
const RTGTransition = /*#__PURE__*/React.forwardRef((_ref, ref) => {
  let {
      component: Component
    } = _ref,
    props = _objectWithoutPropertiesLoose(_ref, _excluded);
  const transitionProps = useRTGTransitionProps(props);
  return /*#__PURE__*/_jsx(Component, Object.assign({
    ref: ref
  }, transitionProps));
});
export default RTGTransition;