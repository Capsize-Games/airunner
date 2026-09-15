import * as React from 'react';
import { DropdownProps as BaseDropdownProps } from '@restart/ui/Dropdown';
import { DropDirection } from './DropdownContext';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { AlignType } from './types';
export interface DropdownProps extends BaseDropdownProps, BsPrefixProps, Omit<React.HTMLAttributes<HTMLElement>, 'onSelect' | 'children' | 'onToggle'> {
    drop?: DropDirection;
    align?: AlignType;
    focusFirstItemOnShow?: boolean | 'keyboard';
    navbar?: boolean;
    autoClose?: boolean | 'outside' | 'inside';
}
declare const _default: BsPrefixRefForwardingComponent<"div", DropdownProps> & {
    Toggle: BsPrefixRefForwardingComponent<"button", import("./DropdownToggle").DropdownToggleProps>;
    Menu: BsPrefixRefForwardingComponent<"div", import("./DropdownMenu").DropdownMenuProps>;
    Item: BsPrefixRefForwardingComponent<"a", import("./DropdownItem").DropdownItemProps>;
    ItemText: BsPrefixRefForwardingComponent<"span", import("./DropdownItemText").DropdownItemTextProps>;
    Divider: BsPrefixRefForwardingComponent<"hr", import("./DropdownDivider").DropdownDividerProps>;
    Header: BsPrefixRefForwardingComponent<"div", import("./DropdownHeader").DropdownHeaderProps>;
};
export default _default;
