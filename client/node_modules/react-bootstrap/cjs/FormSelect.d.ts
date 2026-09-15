import * as React from 'react';
import { BsPrefixOnlyProps, BsPrefixRefForwardingComponent } from './helpers';
export interface FormSelectProps extends BsPrefixOnlyProps, Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
    htmlSize?: number;
    size?: 'sm' | 'lg';
    isValid?: boolean;
    isInvalid?: boolean;
}
declare const FormSelect: BsPrefixRefForwardingComponent<'select', FormSelectProps>;
export default FormSelect;
