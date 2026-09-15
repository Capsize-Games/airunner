import * as React from 'react';
import { EventKey, DynamicRefForwardingComponent, SelectCallback } from './types';
import { UseNavItemOptions, NavItemProps } from './NavItem';
export type { UseNavItemOptions, NavItemProps };
export interface NavProps extends Omit<React.HTMLAttributes<HTMLElement>, 'onSelect'> {
    /**
     * Key for the currently active NavItem.
     */
    activeKey?: EventKey;
    /**
     * Element used to render the component.
     */
    as?: React.ElementType;
    /**
     * A callback fired when a NavItem has been selected.
     */
    onSelect?: SelectCallback;
}
declare const _default: DynamicRefForwardingComponent<"div", NavProps> & {
    Item: DynamicRefForwardingComponent<React.ForwardRefExoticComponent<import("./Button").ButtonProps & React.RefAttributes<HTMLElement>>, NavItemProps>;
};
export default _default;
