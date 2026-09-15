import * as React from 'react';
import { UseDropdownMenuOptions } from '@restart/ui/DropdownMenu';
import { DropDirection } from './DropdownContext';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { AlignType } from './types';
export type DropdownMenuVariant = 'dark' | string;
export interface DropdownMenuProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    show?: boolean;
    renderOnMount?: boolean;
    flip?: boolean;
    align?: AlignType;
    rootCloseEvent?: 'click' | 'mousedown';
    popperConfig?: UseDropdownMenuOptions['popperConfig'];
    variant?: DropdownMenuVariant;
}
export declare function getDropdownMenuPlacement(alignEnd: boolean, dropDirection?: DropDirection, isRTL?: boolean): "bottom" | "top" | "top-start" | "top-end" | "bottom-start" | "bottom-end" | "right-start" | "right-end" | "left-start" | "left-end";
declare const DropdownMenu: BsPrefixRefForwardingComponent<'div', DropdownMenuProps>;
export default DropdownMenu;
