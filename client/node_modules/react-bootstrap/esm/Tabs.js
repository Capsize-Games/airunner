import * as React from 'react';
import { useUncontrolled } from 'uncontrollable';
import BaseTabs from '@restart/ui/Tabs';
import Nav from './Nav';
import NavLink from './NavLink';
import NavItem from './NavItem';
import TabContent from './TabContent';
import TabPane from './TabPane';
import { forEach, map } from './ElementChildren';
import getTabTransitionComponent from './getTabTransitionComponent';
import { jsx as _jsx } from "react/jsx-runtime";
import { jsxs as _jsxs } from "react/jsx-runtime";
function getDefaultActiveKey(children) {
  let defaultActiveKey;
  forEach(children, child => {
    if (defaultActiveKey == null) {
      defaultActiveKey = child.props.eventKey;
    }
  });
  return defaultActiveKey;
}
function renderTab(child) {
  const {
    title,
    eventKey,
    disabled,
    tabClassName,
    tabAttrs,
    id
  } = child.props;
  if (title == null) {
    return null;
  }
  return /*#__PURE__*/_jsx(NavItem, {
    as: "li",
    role: "presentation",
    children: /*#__PURE__*/_jsx(NavLink, {
      as: "button",
      type: "button",
      eventKey: eventKey,
      disabled: disabled,
      id: id,
      className: tabClassName,
      ...tabAttrs,
      children: title
    })
  });
}
const Tabs = props => {
  const {
    id,
    onSelect,
    transition,
    mountOnEnter = false,
    unmountOnExit = false,
    variant = 'tabs',
    children,
    activeKey = getDefaultActiveKey(children),
    ...controlledProps
  } = useUncontrolled(props, {
    activeKey: 'onSelect'
  });
  return /*#__PURE__*/_jsxs(BaseTabs, {
    id: id,
    activeKey: activeKey,
    onSelect: onSelect,
    transition: getTabTransitionComponent(transition),
    mountOnEnter: mountOnEnter,
    unmountOnExit: unmountOnExit,
    children: [/*#__PURE__*/_jsx(Nav, {
      id: id,
      ...controlledProps,
      role: "tablist",
      as: "ul",
      variant: variant,
      children: map(children, renderTab)
    }), /*#__PURE__*/_jsx(TabContent, {
      children: map(children, child => {
        const childProps = {
          ...child.props
        };
        delete childProps.title;
        delete childProps.disabled;
        delete childProps.tabClassName;
        delete childProps.tabAttrs;
        return /*#__PURE__*/_jsx(TabPane, {
          ...childProps
        });
      })
    })]
  });
};
Tabs.displayName = 'Tabs';
export default Tabs;