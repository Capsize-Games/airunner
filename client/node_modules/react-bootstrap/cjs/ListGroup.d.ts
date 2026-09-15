import { NavProps as BaseNavProps } from '@restart/ui/Nav';
import { EventKey } from '@restart/ui/types';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface ListGroupProps extends BsPrefixProps, BaseNavProps {
    variant?: 'flush' | string;
    horizontal?: boolean | string | 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
    defaultActiveKey?: EventKey;
    numbered?: boolean;
}
declare const _default: BsPrefixRefForwardingComponent<"div", ListGroupProps> & {
    Item: BsPrefixRefForwardingComponent<"a", import("./ListGroupItem").ListGroupItemProps>;
};
export default _default;
