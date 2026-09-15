import * as React from 'react';
import { CollapseProps } from './Collapse';
import { BsPrefixProps } from './helpers';
export interface NavbarCollapseProps extends Omit<CollapseProps, 'children'>, React.HTMLAttributes<HTMLDivElement>, BsPrefixProps {
}
declare const NavbarCollapse: React.ForwardRefExoticComponent<NavbarCollapseProps & React.RefAttributes<HTMLDivElement>>;
export default NavbarCollapse;
