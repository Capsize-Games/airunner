"use client";

import classNames from 'classnames';
import * as React from 'react';
import SelectableContext from '@restart/ui/SelectableContext';
import TabContext from '@restart/ui/TabContext';
import { useTabPanel } from '@restart/ui/TabPanel';
import { useBootstrapPrefix } from './ThemeProvider';
import Fade from './Fade';
import getTabTransitionComponent from './getTabTransitionComponent';
import { jsx as _jsx } from "react/jsx-runtime";
const TabPane = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  transition,
  ...props
}, ref) => {
  const [{
    className,
    // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
    as: Component = 'div',
    ...rest
  }, {
    isActive,
    onEnter,
    onEntering,
    onEntered,
    onExit,
    onExiting,
    onExited,
    mountOnEnter,
    unmountOnExit,
    transition: Transition = Fade
  }] = useTabPanel({
    ...props,
    transition: getTabTransitionComponent(transition)
  });
  const prefix = useBootstrapPrefix(bsPrefix, 'tab-pane');

  // We provide an empty the TabContext so `<Nav>`s in `<TabPanel>`s don't
  // conflict with the top level one.
  return /*#__PURE__*/_jsx(TabContext.Provider, {
    value: null,
    children: /*#__PURE__*/_jsx(SelectableContext.Provider, {
      value: null,
      children: /*#__PURE__*/_jsx(Transition, {
        in: isActive,
        onEnter: onEnter,
        onEntering: onEntering,
        onEntered: onEntered,
        onExit: onExit,
        onExiting: onExiting,
        onExited: onExited,
        mountOnEnter: mountOnEnter,
        unmountOnExit: unmountOnExit,
        children: /*#__PURE__*/_jsx(Component, {
          ...rest,
          ref: ref,
          className: classNames(className, prefix, isActive && 'active')
        })
      })
    })
  });
});
TabPane.displayName = 'TabPane';
export default TabPane;