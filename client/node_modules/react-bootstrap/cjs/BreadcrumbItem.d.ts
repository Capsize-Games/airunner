import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface BreadcrumbItemProps extends BsPrefixProps, Omit<React.HTMLAttributes<HTMLElement>, 'title'> {
    active?: boolean;
    href?: string;
    linkAs?: React.ElementType;
    target?: string;
    title?: React.ReactNode;
    linkProps?: Record<string, any>;
}
declare const BreadcrumbItem: BsPrefixRefForwardingComponent<'li', BreadcrumbItemProps>;
export default BreadcrumbItem;
