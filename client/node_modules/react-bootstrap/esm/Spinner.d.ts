import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { Variant } from './types';
export interface SpinnerProps extends React.HTMLAttributes<HTMLElement>, BsPrefixProps {
    animation?: 'border' | 'grow';
    size?: 'sm';
    variant?: Variant;
}
declare const Spinner: BsPrefixRefForwardingComponent<'div', SpinnerProps>;
export default Spinner;
