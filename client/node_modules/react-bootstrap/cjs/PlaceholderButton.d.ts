import { BsPrefixRefForwardingComponent } from './helpers';
import { UsePlaceholderProps } from './usePlaceholder';
import { ButtonVariant } from './types';
export interface PlaceholderButtonProps extends UsePlaceholderProps {
    variant?: ButtonVariant;
}
declare const PlaceholderButton: BsPrefixRefForwardingComponent<'button', PlaceholderButtonProps>;
export default PlaceholderButton;
