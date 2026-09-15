import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface BreadcrumbProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    label?: string;
    listProps?: React.OlHTMLAttributes<HTMLOListElement>;
}
declare const _default: BsPrefixRefForwardingComponent<"nav", BreadcrumbProps> & {
    Item: BsPrefixRefForwardingComponent<"li", import("./BreadcrumbItem").BreadcrumbItemProps>;
};
export default _default;
