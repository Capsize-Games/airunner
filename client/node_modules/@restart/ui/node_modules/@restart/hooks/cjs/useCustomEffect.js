"use strict";

exports.__esModule = true;
exports.default = void 0;
var _react = require("react");
var _useMounted = _interopRequireDefault(require("./useMounted"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
/**
 * a useEffect() hook with customized depedency comparision
 *
 * @param effect The effect callback
 * @param dependencies A list of dependencies
 * @param isEqual A function comparing the next and previous dependencyLists
 */

/**
 * a useEffect() hook with customized depedency comparision
 *
 * @param effect The effect callback
 * @param dependencies A list of dependencies
 * @param options
 * @param options.isEqual A function comparing the next and previous dependencyLists
 * @param options.effectHook the underlying effect hook used, defaults to useEffect
 */

function useCustomEffect(effect, dependencies, isEqualOrOptions) {
  const isMounted = (0, _useMounted.default)();
  const {
    isEqual,
    effectHook = _react.useEffect
  } = typeof isEqualOrOptions === 'function' ? {
    isEqual: isEqualOrOptions
  } : isEqualOrOptions;
  const dependenciesRef = (0, _react.useRef)();
  dependenciesRef.current = dependencies;
  const cleanupRef = (0, _react.useRef)(null);
  effectHook(() => {
    // If the ref the is `null` it's either the first effect or the last effect
    // ran and was cleared, meaning _this_ update should run, b/c the equality
    // check failed on in the cleanup of the last effect.
    if (cleanupRef.current === null) {
      const cleanup = effect();
      cleanupRef.current = () => {
        if (isMounted() && isEqual(dependenciesRef.current, dependencies)) {
          return;
        }
        cleanupRef.current = null;
        if (cleanup) cleanup();
      };
    }
    return cleanupRef.current;
  });
  (0, _react.useDebugValue)(effect);
}
var _default = useCustomEffect;
exports.default = _default;