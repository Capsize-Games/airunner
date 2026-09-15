import * as React from 'react';
import { DropdownContextValue } from './DropdownContext';
import { UsePopperOptions, Placement, Offset, UsePopperState } from './usePopper';
import { ClickOutsideOptions } from './useClickOutside';
export interface UseDropdownMenuOptions {
    /**
     * Enables the Popper.js `flip` modifier, allowing the Dropdown to
     * automatically adjust it's placement in case of overlap with the viewport or
     * toggle. See the [flip docs](https://popper.js.org/docs/v2/modifiers/flip/)
     * for more info.
     */
    flip?: boolean;
    /**
     * Controls the visible state of the menu, generally this is provided by the
     * parent `Dropdown` component, but may also be specified as a prop directly.
     */
    show?: boolean;
    /**
     * Use the `fixed` positioning strategy in Popper. This is used if the
     * dropdown toggle is in a fixed container.
     */
    fixed?: boolean;
    /**
     * The PopperJS placement for positioning the Dropdown menu in relation to it's Toggle.
     * Generally this is provided by the parent `Dropdown` component,
     * but may also be specified as a prop directly.
     */
    placement?: Placement;
    /**
     * Whether or not to use Popper for positioning the menu.
     */
    usePopper?: boolean;
    /**
     * Whether or not to add scroll and resize listeners to update menu position.
     *
     * See the [event listeners docs](https://popper.js.org/docs/v2/modifiers/event-listeners/)
     * for more info.
     */
    enableEventListeners?: boolean;
    /**
     * Offset of the dropdown menu from the dropdown toggle. See the
     * [offset docs](https://popper.js.org/docs/v2/modifiers/offset/) for more info.
     */
    offset?: Offset;
    /**
     * Override the default event used by RootCloseWrapper.
     */
    rootCloseEvent?: ClickOutsideOptions['clickTrigger'];
    /**
     * A set of popper options and props passed directly to react-popper's Popper component.
     */
    popperConfig?: Omit<UsePopperOptions, 'enabled' | 'placement'>;
}
export type UserDropdownMenuProps = Record<string, any> & {
    ref: React.RefCallback<HTMLElement>;
    style?: React.CSSProperties;
    'aria-labelledby'?: string;
};
export type UserDropdownMenuArrowProps = Record<string, any> & {
    ref: React.RefCallback<HTMLElement>;
    style: React.CSSProperties;
};
export interface UseDropdownMenuMetadata {
    show: boolean;
    placement?: Placement;
    hasShown: boolean;
    toggle?: DropdownContextValue['toggle'];
    popper: UsePopperState | null;
    arrowProps: Partial<UserDropdownMenuArrowProps>;
}
/**
 * @memberOf Dropdown
 * @param {object}  options
 * @param {boolean} options.flip Automatically adjust the menu `drop` position based on viewport edge detection
 * @param {[number, number]} options.offset Define an offset distance between the Menu and the Toggle
 * @param {boolean} options.show Display the menu manually, ignored in the context of a `Dropdown`
 * @param {boolean} options.usePopper opt in/out of using PopperJS to position menus. When disabled you must position it yourself.
 * @param {string}  options.rootCloseEvent The pointer event to listen for when determining "clicks outside" the menu for triggering a close.
 * @param {object}  options.popperConfig Options passed to the [`usePopper`](/api/usePopper) hook.
 */
export declare function useDropdownMenu(options?: UseDropdownMenuOptions): readonly [UserDropdownMenuProps, UseDropdownMenuMetadata];
export interface DropdownMenuProps extends UseDropdownMenuOptions {
    /**
     * A render prop that returns a Menu element. The `props`
     * argument should be spread through to **a component that can accept a ref**.
     *
     * @type {Function ({
     *   show: boolean,
     *   close: (?SyntheticEvent) => void,
     *   placement: Placement,
     *   update: () => void,
     *   forceUpdate: () => void,
     *   props: {
     *     ref: (?HTMLElement) => void,
     *     style: { [string]: string | number },
     *     aria-labelledby: ?string
     *   },
     *   arrowProps: {
     *     ref: (?HTMLElement) => void,
     *     style: { [string]: string | number },
     *   },
     * }) => React.Element}
     */
    children: (props: UserDropdownMenuProps, meta: UseDropdownMenuMetadata) => React.ReactNode;
}
/**
 * Also exported as `<Dropdown.Menu>` from `Dropdown`.
 *
 * @displayName DropdownMenu
 * @memberOf Dropdown
 */
declare function DropdownMenu({ children, usePopper: usePopperProp, ...options }: DropdownMenuProps): React.JSX.Element;
declare namespace DropdownMenu {
    var displayName: string;
}
/** @component */
export default DropdownMenu;
