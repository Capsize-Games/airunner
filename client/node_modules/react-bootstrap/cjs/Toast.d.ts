import * as React from 'react';
import { TransitionCallbacks, TransitionComponent } from '@restart/ui/types';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { Variant } from './types';
export interface ToastProps extends TransitionCallbacks, BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    animation?: boolean;
    autohide?: boolean;
    delay?: number;
    onClose?: (e?: React.MouseEvent | React.KeyboardEvent) => void;
    show?: boolean;
    transition?: TransitionComponent;
    bg?: Variant;
}
declare const _default: BsPrefixRefForwardingComponent<"div", ToastProps> & {
    Body: BsPrefixRefForwardingComponent<"div", import("./ToastBody").ToastBodyProps>;
    Header: React.ForwardRefExoticComponent<import("./ToastHeader").ToastHeaderProps & React.RefAttributes<HTMLDivElement>>;
};
export default _default;
