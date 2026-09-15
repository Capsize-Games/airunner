import { useCallback } from 'react';
import useCommittedRef from './useCommittedRef';
export default function useEventCallback(fn) {
  const ref = useCommittedRef(fn);
  return useCallback(function (...args) {
    return ref.current && ref.current(...args);
  }, [ref]);
}