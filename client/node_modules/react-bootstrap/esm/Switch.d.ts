import * as React from 'react';
import { FormCheckProps } from './FormCheck';
import { BsPrefixRefForwardingComponent } from './helpers';
type SwitchProps = Omit<FormCheckProps, 'type'>;
declare const _default: BsPrefixRefForwardingComponent<BsPrefixRefForwardingComponent<"input", FormCheckProps> & {
    Input: BsPrefixRefForwardingComponent<"input", import("./FormCheckInput").FormCheckInputProps>;
    Label: React.ForwardRefExoticComponent<import("./FormCheckLabel").FormCheckLabelProps & React.RefAttributes<HTMLLabelElement>>;
}, SwitchProps> & {
    Input: BsPrefixRefForwardingComponent<"input", import("./FormCheckInput").FormCheckInputProps>;
    Label: React.ForwardRefExoticComponent<import("./FormCheckLabel").FormCheckLabelProps & React.RefAttributes<HTMLLabelElement>>;
};
export default _default;
