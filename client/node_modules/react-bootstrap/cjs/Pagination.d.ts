import * as React from 'react';
import { BsPrefixProps } from './helpers';
export interface PaginationProps extends BsPrefixProps, React.HTMLAttributes<HTMLUListElement> {
    size?: 'sm' | 'lg';
}
declare const _default: React.ForwardRefExoticComponent<PaginationProps & React.RefAttributes<HTMLUListElement>> & {
    First: React.ForwardRefExoticComponent<import("./PageItem").PageItemProps & React.RefAttributes<unknown>>;
    Prev: React.ForwardRefExoticComponent<import("./PageItem").PageItemProps & React.RefAttributes<unknown>>;
    Ellipsis: React.ForwardRefExoticComponent<import("./PageItem").PageItemProps & React.RefAttributes<unknown>>;
    Item: import("./helpers").BsPrefixRefForwardingComponent<"li", import("./PageItem").PageItemProps>;
    Next: React.ForwardRefExoticComponent<import("./PageItem").PageItemProps & React.RefAttributes<unknown>>;
    Last: React.ForwardRefExoticComponent<import("./PageItem").PageItemProps & React.RefAttributes<unknown>>;
};
export default _default;
