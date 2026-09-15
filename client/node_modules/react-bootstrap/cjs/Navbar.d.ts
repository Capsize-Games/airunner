import * as React from 'react';
import { SelectCallback } from '@restart/ui/types';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface NavbarProps extends BsPrefixProps, Omit<React.HTMLAttributes<HTMLElement>, 'onSelect' | 'onToggle'> {
    variant?: 'light' | 'dark' | string;
    expand?: boolean | string | 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
    bg?: string;
    fixed?: 'top' | 'bottom';
    sticky?: 'top' | 'bottom';
    onToggle?: (expanded: boolean) => void;
    onSelect?: SelectCallback;
    collapseOnSelect?: boolean;
    expanded?: boolean;
    defaultExpanded?: boolean;
}
declare const _default: BsPrefixRefForwardingComponent<"nav", NavbarProps> & {
    Brand: BsPrefixRefForwardingComponent<"a", import("./NavbarBrand").NavbarBrandProps>;
    Collapse: React.ForwardRefExoticComponent<import("./NavbarCollapse").NavbarCollapseProps & React.RefAttributes<HTMLDivElement>>;
    Offcanvas: React.ForwardRefExoticComponent<Omit<import("./NavbarOffcanvas").NavbarOffcanvasProps, "ref"> & React.RefAttributes<HTMLDivElement>>;
    Text: BsPrefixRefForwardingComponent<"span", import("./NavbarText").NavbarTextProps>;
    Toggle: BsPrefixRefForwardingComponent<"button", import("./NavbarToggle").NavbarToggleProps>;
};
export default _default;
