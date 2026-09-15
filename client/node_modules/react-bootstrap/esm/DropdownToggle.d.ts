import * as React from 'react';
import { ButtonProps, CommonButtonProps } from './Button';
import { BsPrefixRefForwardingComponent } from './helpers';
export interface DropdownToggleProps extends Omit<ButtonProps, 'as'> {
    as?: React.ElementType;
    split?: boolean;
    childBsPrefix?: string;
}
type DropdownToggleComponent = BsPrefixRefForwardingComponent<'button', DropdownToggleProps>;
export type PropsFromToggle = Partial<Pick<React.ComponentPropsWithRef<DropdownToggleComponent>, CommonButtonProps>>;
declare const DropdownToggle: DropdownToggleComponent;
export default DropdownToggle;
