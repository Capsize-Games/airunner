import * as React from 'react';
import { DropdownProps } from './Dropdown';
import { PropsFromToggle } from './DropdownToggle';
import { DropdownMenuVariant } from './DropdownMenu';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface DropdownButtonProps extends Omit<DropdownProps, 'title'>, PropsFromToggle, BsPrefixProps {
    title: React.ReactNode;
    menuRole?: string;
    renderMenuOnMount?: boolean;
    rootCloseEvent?: 'click' | 'mousedown';
    menuVariant?: DropdownMenuVariant;
    flip?: boolean;
}
/**
 * A convenience component for simple or general use dropdowns. Renders a `Button` toggle and all `children`
 * are passed directly to the default `Dropdown.Menu`. This component accepts all of
 * [`Dropdown`'s props](#dropdown-props).
 *
 * _All unknown props are passed through to the `Dropdown` component._ Only
 * the Button `variant`, `size` and `bsPrefix` props are passed to the toggle,
 * along with menu-related props are passed to the `Dropdown.Menu`
 */
declare const DropdownButton: BsPrefixRefForwardingComponent<'div', DropdownButtonProps>;
export default DropdownButton;
