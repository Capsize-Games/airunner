import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
type FormControlElement = HTMLInputElement | HTMLTextAreaElement;
export interface FormControlProps extends BsPrefixProps, Omit<React.InputHTMLAttributes<FormControlElement>, 'size'> {
    htmlSize?: number;
    size?: 'sm' | 'lg';
    plaintext?: boolean;
    readOnly?: boolean;
    disabled?: boolean;
    value?: string | string[] | number;
    onChange?: React.ChangeEventHandler<FormControlElement>;
    type?: string;
    isValid?: boolean;
    isInvalid?: boolean;
}
declare const _default: BsPrefixRefForwardingComponent<"input", FormControlProps> & {
    Feedback: BsPrefixRefForwardingComponent<"div", import("./Feedback").FeedbackProps>;
};
export default _default;
