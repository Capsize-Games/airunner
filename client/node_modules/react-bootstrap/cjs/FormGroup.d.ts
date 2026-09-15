import * as React from 'react';
import { AsProp, BsPrefixRefForwardingComponent } from './helpers';
export interface FormGroupProps extends React.HTMLAttributes<HTMLElement>, AsProp {
    controlId?: string;
}
declare const FormGroup: BsPrefixRefForwardingComponent<'div', FormGroupProps>;
export default FormGroup;
