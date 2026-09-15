import useMergedRefs from '@restart/hooks/useMergedRefs';
import useEventCallback from '@restart/hooks/useEventCallback';
import useIsomorphicEffect from '@restart/hooks/useIsomorphicEffect';
import React, { useRef, cloneElement, useState } from 'react';
import NoopTransition from './NoopTransition';
import RTGTransition from './RTGTransition';
import { getChildRef } from './utils';
import { jsx as _jsx } from "react/jsx-runtime";
export function useTransition({
  in: inProp,
  onTransition
}) {
  const ref = useRef(null);
  const isInitialRef = useRef(true);
  const handleTransition = useEventCallback(onTransition);
  useIsomorphicEffect(() => {
    if (!ref.current) {
      return undefined;
    }
    let stale = false;
    handleTransition({
      in: inProp,
      element: ref.current,
      initial: isInitialRef.current,
      isStale: () => stale
    });
    return () => {
      stale = true;
    };
  }, [inProp, handleTransition]);
  useIsomorphicEffect(() => {
    isInitialRef.current = false;
    // this is for strict mode
    return () => {
      isInitialRef.current = true;
    };
  }, []);
  return ref;
}
/**
 * Adapts an imperative transition function to a subset of the RTG `<Transition>` component API.
 *
 * ImperativeTransition does not support mounting options or `appear` at the moment, meaning
 * that it always acts like: `mountOnEnter={true} unmountOnExit={true} appear={true}`
 */
export default function ImperativeTransition({
  children,
  in: inProp,
  onExited,
  onEntered,
  transition
}) {
  const [exited, setExited] = useState(!inProp);

  // TODO: I think this needs to be in an effect
  if (inProp && exited) {
    setExited(false);
  }
  const ref = useTransition({
    in: !!inProp,
    onTransition: options => {
      const onFinish = () => {
        if (options.isStale()) return;
        if (options.in) {
          onEntered == null ? void 0 : onEntered(options.element, options.initial);
        } else {
          setExited(true);
          onExited == null ? void 0 : onExited(options.element);
        }
      };
      Promise.resolve(transition(options)).then(onFinish, error => {
        if (!options.in) setExited(true);
        throw error;
      });
    }
  });
  const combinedRef = useMergedRefs(ref, getChildRef(children));
  return exited && !inProp ? null : /*#__PURE__*/cloneElement(children, {
    ref: combinedRef
  });
}
export function renderTransition(component, runTransition, props) {
  if (component) {
    return /*#__PURE__*/_jsx(RTGTransition, Object.assign({}, props, {
      component: component
    }));
  }
  if (runTransition) {
    return /*#__PURE__*/_jsx(ImperativeTransition, Object.assign({}, props, {
      transition: runTransition
    }));
  }
  return /*#__PURE__*/_jsx(NoopTransition, Object.assign({}, props));
}