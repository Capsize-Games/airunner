import useIsomorphicEffect from '@restart/hooks/useIsomorphicEffect';
import getScrollParent from 'dom-helpers/scrollParent';
import { useState } from 'react';
export default function useScrollParent(element) {
  const [parent, setParent] = useState(null);
  useIsomorphicEffect(() => {
    if (element) {
      setParent(getScrollParent(element, true));
    }
  }, [element]);
  return parent;
}