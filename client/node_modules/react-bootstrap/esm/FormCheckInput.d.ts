import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
type FormCheckInputType = 'checkbox' | 'radio';
export interface FormCheckInputProps extends BsPrefixProps, React.InputHTMLAttributes<HTMLInputElement> {
    type?: FormCheckInputType;
    isValid?: boolean;
    isInvalid?: boolean;
}
declare const FormCheckInput: BsPrefixRefForwardingComponent<'input', FormCheckInputProps>;
export default FormCheckInput;
