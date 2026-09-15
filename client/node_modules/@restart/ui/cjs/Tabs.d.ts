import * as React from 'react';
import { EventKey, SelectCallback, TransitionComponent } from './types';
import { TabPanelProps } from './TabPanel';
export type { TabPanelProps };
export interface TabsProps extends React.PropsWithChildren<unknown> {
    id?: string;
    /**
     * Sets a default animation strategy for all children `<TabPanel>`s.
     * Use a react-transition-group `<Transition/>` component.
     */
    transition?: TransitionComponent;
    /**
     * Wait until the first "enter" transition to mount tabs (add them to the DOM)
     */
    mountOnEnter?: boolean;
    /**
     * Unmount tabs (remove it from the DOM) when they are no longer visible
     */
    unmountOnExit?: boolean;
    /**
     * A function that takes an `eventKey` and `type` and returns a unique id for
     * child tab `<NavItem>`s and `<TabPane>`s. The function _must_ be a pure
     * function, meaning it should always return the _same_ id for the same set
     * of inputs. The default value requires that an `id` to be set for the
     * `<TabContainer>`.
     *
     * The `type` argument will either be `"tab"` or `"pane"`.
     *
     * @defaultValue (eventKey, type) => `${props.id}-${type}-${eventKey}`
     */
    generateChildId?: (eventKey: EventKey, type: 'tab' | 'pane') => string;
    /**
     * A callback fired when a tab is selected.
     *
     * @controllable activeKey
     */
    onSelect?: SelectCallback;
    /**
     * The `eventKey` of the currently active tab.
     *
     * @controllable onSelect
     */
    activeKey?: EventKey;
    /**
     * Default value for `eventKey`.
     */
    defaultActiveKey?: EventKey;
}
declare const Tabs: {
    (props: TabsProps): React.JSX.Element;
    Panel: import("./types").DynamicRefForwardingComponent<"div", TabPanelProps>;
};
export default Tabs;
