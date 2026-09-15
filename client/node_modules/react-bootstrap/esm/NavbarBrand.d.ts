import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface NavbarBrandProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    href?: string;
}
declare const NavbarBrand: BsPrefixRefForwardingComponent<'a', NavbarBrandProps>;
export default NavbarBrand;
