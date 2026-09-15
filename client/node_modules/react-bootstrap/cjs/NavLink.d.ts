import { NavItemProps as BaseNavItemProps } from '@restart/ui/NavItem';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface NavLinkProps extends BsPrefixProps, Omit<BaseNavItemProps, 'as'> {
}
declare const NavLink: BsPrefixRefForwardingComponent<'a', NavLinkProps>;
export default NavLink;
