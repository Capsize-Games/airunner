import * as React from 'react';
import DropdownMenu, { DropdownMenuProps, UseDropdownMenuMetadata, UseDropdownMenuOptions } from './DropdownMenu';
import DropdownToggle, { DropdownToggleProps, UseDropdownToggleMetadata } from './DropdownToggle';
import { DropdownItemProps } from './DropdownItem';
import { SelectCallback } from './types';
import { Placement } from './usePopper';
export type { DropdownMenuProps, UseDropdownMenuMetadata, UseDropdownMenuOptions, DropdownToggleProps, UseDropdownToggleMetadata, DropdownItemProps, };
export interface DropdownInjectedProps {
    onKeyDown: React.KeyboardEventHandler;
}
export type ToggleEvent = React.SyntheticEvent | KeyboardEvent | MouseEvent;
export interface ToggleMetadata {
    source: string | undefined;
    originalEvent: ToggleEvent | undefined;
}
export interface DropdownProps {
    /**
     * The PopperJS placement for positioning the Dropdown menu in relation to
     * its Toggle.
     *
     * @default 'bottom-start'
     */
    placement?: Placement;
    /**
     * Sets the initial visibility of the Dropdown.
     */
    defaultShow?: boolean;
    /**
     * Whether or not the Dropdown is visible.
     *
     * @controllable onToggle
     */
    show?: boolean;
    /**
     * A callback fired when a DropdownItem has been selected.
     */
    onSelect?: SelectCallback;
    /**
     * A callback fired when the Dropdown wishes to change visibility. Called with
     * the requested `show` value, the DOM event, and the source that fired it:
     * `'click'`,`'keydown'`,`'rootClose'`, or `'select'`.
     *
     * ```ts static
     * function(
     *   nextShow: boolean,
     *   meta: ToggleMetadata,
     * ): void
     * ```
     *
     * @controllable show
     */
    onToggle?: (nextShow: boolean, meta: ToggleMetadata) => void;
    /**
     * A css selector string that will return __focusable__ menu items.
     * Selectors should be relative to the menu component:
     * e.g. ` > li:not('.disabled')`
     */
    itemSelector?: string;
    /**
     * Controls the focus behavior for when the Dropdown is opened. Set to
     * `true` to always focus the first menu item, `keyboard` to focus only when
     * navigating via the keyboard, or `false` to disable completely
     *
     * The Default behavior is `false` **unless** the Menu has a `role="menu"`
     * where it will default to `keyboard` to match the recommended [ARIA Authoring
     * practices](https://www.w3.org/TR/wai-aria-practices-1.1/#menubutton).
     */
    focusFirstItemOnShow?: boolean | 'keyboard';
    /**
     * A render prop that returns the root dropdown element. The `props`
     * argument should spread through to an element containing _both_ the
     * menu and toggle in order to handle keyboard events for focus management.
     *
     * @type {Function ({
     *   props: {
     *     onKeyDown: (SyntheticEvent) => void,
     *   },
     * }) => React.Element}
     */
    children: React.ReactNode;
}
/**
 * @displayName Dropdown
 * @public
 */
declare function Dropdown({ defaultShow, show: rawShow, onSelect, onToggle: rawOnToggle, itemSelector, focusFirstItemOnShow, placement, children, }: DropdownProps): React.JSX.Element;
declare namespace Dropdown {
    var displayName: string;
    var Menu: typeof DropdownMenu;
    var Toggle: typeof DropdownToggle;
    var Item: import("./types").DynamicRefForwardingComponent<React.ForwardRefExoticComponent<import("./Button").ButtonProps & React.RefAttributes<HTMLElement>>, DropdownItemProps>;
}
export default Dropdown;
