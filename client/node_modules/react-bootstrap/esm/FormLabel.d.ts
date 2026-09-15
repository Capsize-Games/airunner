import * as React from 'react';
import { ColProps } from './Col';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
interface FormLabelBaseProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    htmlFor?: string;
    visuallyHidden?: boolean;
}
export interface FormLabelOwnProps extends FormLabelBaseProps {
    column?: false;
}
export interface FormLabelWithColProps extends FormLabelBaseProps, ColProps {
    column: true | 'sm' | 'lg';
}
export type FormLabelProps = FormLabelWithColProps | FormLabelOwnProps;
declare const FormLabel: BsPrefixRefForwardingComponent<'label', FormLabelProps>;
export default FormLabel;
