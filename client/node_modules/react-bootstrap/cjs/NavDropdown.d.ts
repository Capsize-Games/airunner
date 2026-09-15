import * as React from 'react';
import { DropdownProps } from './Dropdown';
import { DropdownMenuVariant } from './DropdownMenu';
import { BsPrefixRefForwardingComponent } from './helpers';
export interface NavDropdownProps extends Omit<DropdownProps, 'title'> {
    title: React.ReactNode;
    disabled?: boolean;
    active?: boolean;
    menuRole?: string;
    renderMenuOnMount?: boolean;
    rootCloseEvent?: 'click' | 'mousedown';
    menuVariant?: DropdownMenuVariant;
}
declare const _default: BsPrefixRefForwardingComponent<"div", NavDropdownProps> & {
    Item: BsPrefixRefForwardingComponent<"a", import("./DropdownItem").DropdownItemProps>;
    ItemText: BsPrefixRefForwardingComponent<"span", import("./DropdownItemText").DropdownItemTextProps>;
    Divider: BsPrefixRefForwardingComponent<"hr", import("./DropdownDivider").DropdownDividerProps>;
    Header: BsPrefixRefForwardingComponent<"div", import("./DropdownHeader").DropdownHeaderProps>;
};
export default _default;
