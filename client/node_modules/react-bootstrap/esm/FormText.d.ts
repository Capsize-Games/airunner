import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface FormTextProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    muted?: boolean;
}
declare const FormText: BsPrefixRefForwardingComponent<'small', FormTextProps>;
export default FormText;
