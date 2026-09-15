import * as React from 'react';
import { NavItemProps as BaseNavItemProps } from '@restart/ui/NavItem';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { Variant } from './types';
export interface ListGroupItemProps extends Omit<BaseNavItemProps, 'onSelect'>, BsPrefixProps {
    action?: boolean;
    onClick?: React.MouseEventHandler;
    variant?: Variant;
}
declare const ListGroupItem: BsPrefixRefForwardingComponent<'a', ListGroupItemProps>;
export default ListGroupItem;
