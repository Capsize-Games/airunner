import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { UsePlaceholderProps } from './usePlaceholder';
export interface PlaceholderProps extends UsePlaceholderProps, BsPrefixProps {
}
declare const _default: BsPrefixRefForwardingComponent<"span", PlaceholderProps> & {
    Button: BsPrefixRefForwardingComponent<"button", import("./PlaceholderButton").PlaceholderButtonProps>;
};
export default _default;
