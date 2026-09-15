import { useRef } from 'react';

/**
 * Returns a ref that is immediately updated with the new value
 *
 * @param value The Ref value
 * @category refs
 */
export default function useUpdatedRef(value) {
  const valueRef = useRef(value);
  valueRef.current = value;
  return valueRef;
}