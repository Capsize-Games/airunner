import * as React from 'react';
import { EventKey, DynamicRefForwardingComponent, TransitionCallbacks, TransitionComponent } from './types';
export interface TabPanelProps extends TransitionCallbacks, React.HTMLAttributes<HTMLElement> {
    /**
     * Element used to render the component.
     */
    as?: React.ElementType;
    /**
     * A key that associates the `TabPanel` with it's controlling `NavLink`.
     */
    eventKey?: EventKey;
    /**
     * Toggles the active state of the TabPanel, this is generally controlled by `Tabs`.
     */
    active?: boolean;
    /**
     * Use animation when showing or hiding `<TabPanel>`s. Use a react-transition-group
     * `<Transition/>` component.
     */
    transition?: TransitionComponent;
    /**
     * Wait until the first "enter" transition to mount the tab (add it to the DOM)
     */
    mountOnEnter?: boolean;
    /**
     * Unmount the tab (remove it from the DOM) when it is no longer visible
     */
    unmountOnExit?: boolean;
}
export interface TabPanelMetadata extends TransitionCallbacks {
    eventKey?: EventKey;
    isActive?: boolean;
    transition?: TransitionComponent;
    mountOnEnter?: boolean;
    unmountOnExit?: boolean;
}
export declare function useTabPanel({ active, eventKey, mountOnEnter, transition, unmountOnExit, role, onEnter, onEntering, onEntered, onExit, onExiting, onExited, ...props }: TabPanelProps): [any, TabPanelMetadata];
declare const TabPanel: DynamicRefForwardingComponent<'div', TabPanelProps>;
export default TabPanel;
