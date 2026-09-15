import { useCallback, useMemo, useRef } from 'react';
import useEventCallback from './useEventCallback';
import useMounted from './useMounted';
/**
 * useFocusManager provides a way to track and manage focus as it moves around
 * a container element. An `onChange` is fired when focus enters or leaves the
 * element, but not when it moves around inside the element, similar to
 * `pointerenter` and `pointerleave` DOM events.
 *
 * ```tsx
 * const [focused, setFocusState] = useState(false)
 *
 * const { onBlur, onFocus } = useFocusManager({
 *   onChange: nextFocused => setFocusState(nextFocused)
 * })
 *
 * return (
 *   <div tabIndex="-1" onFocus={onFocus} onBlur={onBlur}>
 *     {String(focused)}
 *     <input />
 *     <input />
 *
 *     <button>A button</button>
 *   </div>
 * ```
 *
 * @returns a memoized FocusController containing event handlers
 */
export default function useFocusManager(opts) {
  const isMounted = useMounted();
  const lastFocused = useRef();
  const handle = useRef();
  const willHandle = useEventCallback(opts.willHandle);
  const didHandle = useEventCallback(opts.didHandle);
  const onChange = useEventCallback(opts.onChange);
  const isDisabled = useEventCallback(opts.isDisabled);
  const handleChange = useCallback((focused, event) => {
    if (focused !== lastFocused.current) {
      didHandle == null ? void 0 : didHandle(focused, event);

      // only fire a change when unmounted if its a blur
      if (isMounted() || !focused) {
        lastFocused.current = focused;
        onChange == null ? void 0 : onChange(focused, event);
      }
    }
  }, [isMounted, didHandle, onChange, lastFocused]);
  const handleFocusChange = useCallback((focused, event) => {
    if (isDisabled()) return;
    if (event && event.persist) event.persist();
    if ((willHandle == null ? void 0 : willHandle(focused, event)) === false) {
      return;
    }
    clearTimeout(handle.current);
    if (focused) {
      handleChange(focused, event);
    } else {
      handle.current = window.setTimeout(() => handleChange(focused, event));
    }
  }, [willHandle, handleChange]);
  return useMemo(() => ({
    onBlur: event => {
      handleFocusChange(false, event);
    },
    onFocus: event => {
      handleFocusChange(true, event);
    }
  }), [handleFocusChange]);
}