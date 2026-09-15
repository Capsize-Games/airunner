import * as React from 'react';
import { EventKey, DynamicRefForwardingComponent } from './types';
import Button from './Button';
export interface NavItemProps extends React.HTMLAttributes<HTMLElement> {
    /**
     * Highlight the NavItem as active.
     */
    active?: boolean;
    /**
     * Element used to render the component.
     */
    as?: React.ElementType;
    /**
     * Disable the NavItem, making it unselectable.
     */
    disabled?: boolean;
    /**
     * Value passed to the `onSelect` handler, useful for identifying the selected NavItem.
     */
    eventKey?: EventKey;
    /**
     * HTML `href` attribute corresponding to `a.href`.
     */
    href?: string;
}
export interface UseNavItemOptions {
    key?: string | null;
    onClick?: React.MouseEventHandler;
    active?: boolean;
    disabled?: boolean;
    id?: string;
    role?: string;
}
export declare function useNavItem({ key, onClick, active, id, role, disabled, }: UseNavItemOptions): readonly [any, {
    readonly isActive: boolean | undefined;
}];
declare const NavItem: DynamicRefForwardingComponent<typeof Button, NavItemProps>;
export default NavItem;
