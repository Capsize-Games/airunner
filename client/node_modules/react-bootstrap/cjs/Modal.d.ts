import * as React from 'react';
import { BaseModalProps } from '@restart/ui/Modal';
import { BsPrefixRefForwardingComponent } from './helpers';
export interface ModalProps extends Omit<BaseModalProps, 'role' | 'renderBackdrop' | 'renderDialog' | 'transition' | 'backdropTransition' | 'children'> {
    size?: 'sm' | 'lg' | 'xl';
    fullscreen?: true | string | 'sm-down' | 'md-down' | 'lg-down' | 'xl-down' | 'xxl-down';
    bsPrefix?: string;
    centered?: boolean;
    backdropClassName?: string;
    animation?: boolean;
    dialogClassName?: string;
    contentClassName?: string;
    dialogAs?: React.ElementType;
    scrollable?: boolean;
    [other: string]: any;
}
declare const _default: BsPrefixRefForwardingComponent<"div", ModalProps> & {
    Body: BsPrefixRefForwardingComponent<"div", import("./ModalBody").ModalBodyProps>;
    Header: React.ForwardRefExoticComponent<import("./ModalHeader").ModalHeaderProps & React.RefAttributes<HTMLDivElement>>;
    Title: BsPrefixRefForwardingComponent<"span", import("./ModalTitle").ModalTitleProps>;
    Footer: BsPrefixRefForwardingComponent<"div", import("./ModalFooter").ModalFooterProps>;
    Dialog: React.ForwardRefExoticComponent<import("./ModalDialog").ModalDialogProps & React.RefAttributes<HTMLDivElement>>;
    TRANSITION_DURATION: number;
    BACKDROP_TRANSITION_DURATION: number;
};
export default _default;
