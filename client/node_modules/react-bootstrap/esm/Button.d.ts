import { ButtonProps as BaseButtonProps } from '@restart/ui/Button';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { ButtonVariant } from './types';
export interface ButtonProps extends BaseButtonProps, Omit<BsPrefixProps, 'as'> {
    active?: boolean;
    variant?: ButtonVariant;
    size?: 'sm' | 'lg';
}
export type CommonButtonProps = 'href' | 'size' | 'variant' | 'disabled';
declare const Button: BsPrefixRefForwardingComponent<'button', ButtonProps>;
export default Button;
