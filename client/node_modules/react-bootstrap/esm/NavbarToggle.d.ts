import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface NavbarToggleProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    label?: string;
}
declare const NavbarToggle: BsPrefixRefForwardingComponent<'button', NavbarToggleProps>;
export default NavbarToggle;
