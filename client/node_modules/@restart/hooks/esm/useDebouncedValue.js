import { useEffect, useDebugValue, useRef } from 'react';
import useDebouncedState from './useDebouncedState';
const defaultIsEqual = (a, b) => a === b;
/**
 * Debounce a value change by a specified number of milliseconds. Useful
 * when you want need to trigger a change based on a value change, but want
 * to defer changes until the changes reach some level of infrequency.
 *
 * @param value
 * @param waitOrOptions
 * @returns
 */
function useDebouncedValue(value, waitOrOptions = 500) {
  const previousValueRef = useRef(value);
  const isEqual = typeof waitOrOptions === 'object' ? waitOrOptions.isEqual || defaultIsEqual : defaultIsEqual;
  const [debouncedValue, setDebouncedValue] = useDebouncedState(value, waitOrOptions);
  useDebugValue(debouncedValue);
  useEffect(() => {
    if (!isEqual || !isEqual(previousValueRef.current, value)) {
      previousValueRef.current = value;
      setDebouncedValue(value);
    }
  });
  return debouncedValue;
}
export default useDebouncedValue;