import * as React from 'react';
import { ModalProps as BaseModalProps } from '@restart/ui/Modal';
import { BsPrefixRefForwardingComponent } from './helpers';
export type OffcanvasPlacement = 'start' | 'end' | 'top' | 'bottom';
export interface OffcanvasProps extends Omit<BaseModalProps, 'role' | 'renderBackdrop' | 'renderDialog' | 'transition' | 'backdrop' | 'backdropTransition'> {
    bsPrefix?: string;
    backdropClassName?: string;
    scroll?: boolean;
    placement?: OffcanvasPlacement;
    responsive?: 'sm' | 'md' | 'lg' | 'xl' | 'xxl' | string;
    renderStaticNode?: boolean;
}
declare const _default: BsPrefixRefForwardingComponent<"div", OffcanvasProps> & {
    Body: BsPrefixRefForwardingComponent<"div", import("./OffcanvasBody").OffcanvasBodyProps>;
    Header: React.ForwardRefExoticComponent<import("./OffcanvasHeader").OffcanvasHeaderProps & React.RefAttributes<HTMLDivElement>>;
    Title: BsPrefixRefForwardingComponent<"div", import("./OffcanvasTitle").OffcanvasTitleProps>;
};
export default _default;
