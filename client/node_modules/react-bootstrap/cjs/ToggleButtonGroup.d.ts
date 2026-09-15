import * as React from 'react';
import { ButtonGroupProps } from './ButtonGroup';
import { BsPrefixRefForwardingComponent } from './helpers';
type BaseToggleButtonProps = Omit<ButtonGroupProps, 'toggle' | 'defaultValue' | 'onChange'>;
export interface ToggleButtonRadioProps<T> extends BaseToggleButtonProps {
    type?: 'radio';
    name: string;
    value?: T;
    defaultValue?: T;
    onChange?: (value: T, event: any) => void;
}
export interface ToggleButtonCheckboxProps<T> extends BaseToggleButtonProps {
    type: 'checkbox';
    name?: string;
    value?: T[];
    defaultValue?: T[];
    onChange?: (value: T[]) => void;
}
export type ToggleButtonGroupProps<T> = ToggleButtonRadioProps<T> | ToggleButtonCheckboxProps<T>;
declare const _default: BsPrefixRefForwardingComponent<"a", ToggleButtonGroupProps<any>> & {
    Button: React.ForwardRefExoticComponent<import("./ToggleButton").ToggleButtonProps & React.RefAttributes<HTMLLabelElement>>;
};
export default _default;
