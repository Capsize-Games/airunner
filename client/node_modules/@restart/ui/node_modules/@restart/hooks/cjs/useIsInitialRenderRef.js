"use strict";

exports.__esModule = true;
exports.default = useIsInitialRenderRef;
var _react = require("react");
/**
 * Returns ref that is `true` on the initial render and `false` on subsequent renders. It
 * is StrictMode safe, so will reset correctly if the component is unmounted and remounted.
 *
 * This hook *must* be used before any effects that read it's value to be accurate.
 */
function useIsInitialRenderRef() {
  const effectCount = (0, _react.useRef)(0);
  const isInitialRenderRef = (0, _react.useRef)(true);
  (0, _react.useLayoutEffect)(() => {
    effectCount.current += 1;
    if (effectCount.current >= 2) {
      isInitialRenderRef.current = false;
    }
  });

  // Strict mode handling in React 18
  (0, _react.useEffect)(() => () => {
    effectCount.current = 0;
    isInitialRenderRef.current = true;
  }, []);
  return isInitialRenderRef;
}