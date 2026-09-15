import { DropdownItemProps as BaseDropdownItemProps } from '@restart/ui/DropdownItem';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface DropdownItemProps extends BaseDropdownItemProps, BsPrefixProps {
}
declare const DropdownItem: BsPrefixRefForwardingComponent<'a', DropdownItemProps>;
export default DropdownItem;
