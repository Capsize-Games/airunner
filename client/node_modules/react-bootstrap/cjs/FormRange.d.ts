import * as React from 'react';
import { BsPrefixOnlyProps } from './helpers';
export interface FormRangeProps extends BsPrefixOnlyProps, Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
}
declare const FormRange: React.ForwardRefExoticComponent<FormRangeProps & React.RefAttributes<HTMLInputElement>>;
export default FormRange;
