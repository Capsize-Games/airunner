const _excluded = ["renderComponent", "onPositionChange"];
function _objectWithoutPropertiesLoose(r, e) { if (null == r) return {}; var t = {}; for (var n in r) if ({}.hasOwnProperty.call(r, n)) { if (e.indexOf(n) >= 0) continue; t[n] = r[n]; } return t; }
import useCallbackRef from '@restart/hooks/useCallbackRef';
import * as React from 'react';
import useWaypoint, { Position } from './useWaypoint';
import { jsx as _jsx } from "react/jsx-runtime";
export { Position };
const defaultRenderComponent = ref => /*#__PURE__*/_jsx("span", {
  ref: ref,
  style: {
    fontSize: 0
  }
});
/**
 * A component that tracks when it enters or leaves the viewport. Implemented
 * using IntersectionObserver, polyfill may be required for older browsers.
 */
function Waypoint(_ref) {
  let {
      renderComponent = defaultRenderComponent,
      onPositionChange
    } = _ref,
    options = _objectWithoutPropertiesLoose(_ref, _excluded);
  const [element, setElement] = useCallbackRef();
  useWaypoint(element, onPositionChange, options);
  return renderComponent(setElement);
}
export default Waypoint;