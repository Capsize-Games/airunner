import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface PageItemProps extends React.HTMLAttributes<HTMLElement>, BsPrefixProps {
    disabled?: boolean;
    active?: boolean;
    activeLabel?: string;
    href?: string;
    linkStyle?: React.CSSProperties;
    linkClassName?: string;
}
declare const PageItem: BsPrefixRefForwardingComponent<'li', PageItemProps>;
export default PageItem;
export declare const First: React.ForwardRefExoticComponent<PageItemProps & React.RefAttributes<unknown>>;
export declare const Prev: React.ForwardRefExoticComponent<PageItemProps & React.RefAttributes<unknown>>;
export declare const Ellipsis: React.ForwardRefExoticComponent<PageItemProps & React.RefAttributes<unknown>>;
export declare const Next: React.ForwardRefExoticComponent<PageItemProps & React.RefAttributes<unknown>>;
export declare const Last: React.ForwardRefExoticComponent<PageItemProps & React.RefAttributes<unknown>>;
