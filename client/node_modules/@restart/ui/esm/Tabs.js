import * as React from 'react';
import { useMemo } from 'react';
import { useUncontrolledProp } from 'uncontrollable';
import { useSSRSafeId } from './ssr';
import TabContext from './TabContext';
import SelectableContext from './SelectableContext';
import TabPanel from './TabPanel';
import { jsx as _jsx } from "react/jsx-runtime";
const Tabs = props => {
  const {
    id: userId,
    generateChildId: generateCustomChildId,
    onSelect: propsOnSelect,
    activeKey: propsActiveKey,
    defaultActiveKey,
    transition,
    mountOnEnter,
    unmountOnExit,
    children
  } = props;
  const [activeKey, onSelect] = useUncontrolledProp(propsActiveKey, defaultActiveKey, propsOnSelect);
  const id = useSSRSafeId(userId);
  const generateChildId = useMemo(() => generateCustomChildId || ((key, type) => id ? `${id}-${type}-${key}` : null), [id, generateCustomChildId]);
  const tabContext = useMemo(() => ({
    onSelect,
    activeKey,
    transition,
    mountOnEnter: mountOnEnter || false,
    unmountOnExit: unmountOnExit || false,
    getControlledId: key => generateChildId(key, 'tabpane'),
    getControllerId: key => generateChildId(key, 'tab')
  }), [onSelect, activeKey, transition, mountOnEnter, unmountOnExit, generateChildId]);
  return /*#__PURE__*/_jsx(TabContext.Provider, {
    value: tabContext,
    children: /*#__PURE__*/_jsx(SelectableContext.Provider, {
      value: onSelect || null,
      children: children
    })
  });
};
Tabs.Panel = TabPanel;
export default Tabs;