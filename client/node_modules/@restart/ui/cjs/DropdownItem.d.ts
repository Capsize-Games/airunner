import * as React from 'react';
import { EventKey, DynamicRefForwardingComponent } from './types';
import Button from './Button';
export interface DropdownItemProps extends React.HTMLAttributes<HTMLElement> {
    /**
     * Element used to render the component.
     */
    as?: React.ElementType;
    /**
     * Highlight the menu item as active.
     */
    active?: boolean;
    /**
     * Disable the menu item, making it unselectable.
     */
    disabled?: boolean;
    /**
     * Value passed to the `onSelect` handler, useful for identifying the selected menu item.
     */
    eventKey?: EventKey;
    /**
     * HTML `href` attribute corresponding to `a.href`.
     */
    href?: string;
}
interface UseDropdownItemOptions {
    key?: EventKey | null;
    href?: string;
    active?: boolean;
    disabled?: boolean;
    onClick?: React.MouseEventHandler;
}
/**
 * Create a dropdown item. Returns a set of props for the dropdown item component
 * including an `onClick` handler that prevents selection when the item is disabled
 */
export declare function useDropdownItem({ key, href, active, disabled, onClick, }: UseDropdownItemOptions): readonly [{
    readonly onClick: (event: any) => void;
    readonly 'aria-disabled': true | undefined;
    readonly 'aria-selected': boolean | undefined;
    readonly "data-rr-ui-dropdown-item": "";
}, {
    readonly isActive: boolean | undefined;
}];
declare const DropdownItem: DynamicRefForwardingComponent<typeof Button, DropdownItemProps>;
export default DropdownItem;
