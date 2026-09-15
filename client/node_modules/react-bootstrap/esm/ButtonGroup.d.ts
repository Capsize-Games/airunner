import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface ButtonGroupProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    size?: 'sm' | 'lg';
    vertical?: boolean;
}
declare const ButtonGroup: BsPrefixRefForwardingComponent<'div', ButtonGroupProps>;
export default ButtonGroup;
