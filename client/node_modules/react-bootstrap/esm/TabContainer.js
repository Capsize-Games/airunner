import Tabs from '@restart/ui/Tabs';
import getTabTransitionComponent from './getTabTransitionComponent';
import { jsx as _jsx } from "react/jsx-runtime";
const TabContainer = ({
  transition,
  ...props
}) => /*#__PURE__*/_jsx(Tabs, {
  ...props,
  transition: getTabTransitionComponent(transition)
});
TabContainer.displayName = 'TabContainer';
export default TabContainer;