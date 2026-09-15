import * as React from 'react';
import { DropdownContextValue } from './DropdownContext';
export declare const isRoleMenu: (el: HTMLElement) => boolean;
export interface UseDropdownToggleProps {
    id: string;
    ref: DropdownContextValue['setToggle'];
    onClick: React.MouseEventHandler;
    'aria-expanded': boolean;
    'aria-haspopup'?: true;
}
export interface UseDropdownToggleMetadata {
    show: DropdownContextValue['show'];
    toggle: DropdownContextValue['toggle'];
}
/**
 * Wires up Dropdown toggle functionality, returning a set a props to attach
 * to the element that functions as the dropdown toggle (generally a button).
 *
 * @memberOf Dropdown
 */
export declare function useDropdownToggle(): [
    UseDropdownToggleProps,
    UseDropdownToggleMetadata
];
export interface DropdownToggleProps {
    /**
     * A render prop that returns a Toggle element. The `props`
     * argument should spread through to **a component that can accept a ref**. Use
     * the `onToggle` argument to toggle the menu open or closed
     *
     * @type {Function ({
     *   props: {
     *     ref: (?HTMLElement) => void,
     *     aria-haspopup: true
     *     aria-expanded: boolean
     *   },
     *   meta: {
     *     show: boolean,
     *     toggle: (show: boolean) => void,
     *   }
     * }) => React.Element}
     */
    children: (props: UseDropdownToggleProps, meta: UseDropdownToggleMetadata) => React.ReactNode;
}
/**
 * Also exported as `<Dropdown.Toggle>` from `Dropdown`.
 *
 * @displayName DropdownToggle
 * @memberOf Dropdown
 */
declare function DropdownToggle({ children }: DropdownToggleProps): React.JSX.Element;
declare namespace DropdownToggle {
    var displayName: string;
}
/** @component */
export default DropdownToggle;
