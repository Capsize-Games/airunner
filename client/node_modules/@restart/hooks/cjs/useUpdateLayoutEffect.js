"use strict";

exports.__esModule = true;
exports.default = void 0;
var _react = require("react");
/**
 * Runs a layout effect only when the dependencies have changed, skipping the
 * initial "on mount" run. Caution, if the dependency list never changes,
 * the effect is **never run**
 *
 * ```ts
 *  const ref = useRef<HTMLInput>(null);
 *
 *  // focuses an element only if the focus changes, and not on mount
 *  useUpdateLayoutEffect(() => {
 *    const element = ref.current?.children[focusedIdx] as HTMLElement
 *
 *    element?.focus()
 *
 *  }, [focusedIndex])
 * ```
 * @param effect An effect to run on mount
 *
 * @category effects
 */
function useUpdateLayoutEffect(fn, deps) {
  const isFirst = (0, _react.useRef)(true);
  (0, _react.useLayoutEffect)(() => {
    if (isFirst.current) {
      isFirst.current = false;
      return;
    }
    return fn();
  }, deps);
}
var _default = useUpdateLayoutEffect;
exports.default = _default;