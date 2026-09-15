import * as React from 'react';
import { FormGroupProps } from './FormGroup';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface FloatingLabelProps extends FormGroupProps, BsPrefixProps {
    controlId?: string;
    label: React.ReactNode;
}
declare const FloatingLabel: BsPrefixRefForwardingComponent<'div', FloatingLabelProps>;
export default FloatingLabel;
