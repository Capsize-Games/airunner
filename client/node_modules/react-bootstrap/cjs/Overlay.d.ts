import * as React from 'react';
import { OverlayProps as BaseOverlayProps, OverlayArrowProps } from '@restart/ui/Overlay';
import { TransitionType } from './helpers';
import { Placement, PopperRef, RootCloseEvent } from './types';
export interface OverlayInjectedProps {
    ref: React.RefCallback<HTMLElement>;
    style: React.CSSProperties;
    'aria-labelledby'?: string;
    arrowProps: Partial<OverlayArrowProps>;
    show: boolean;
    placement: Placement | undefined;
    popper: PopperRef;
    hasDoneInitialMeasure?: boolean;
    [prop: string]: any;
}
export type OverlayChildren = React.ReactElement<OverlayInjectedProps> | ((injected: OverlayInjectedProps) => React.ReactNode);
export interface OverlayProps extends Omit<BaseOverlayProps, 'children' | 'transition' | 'rootCloseEvent'> {
    children: OverlayChildren;
    transition?: TransitionType;
    placement?: Placement;
    rootCloseEvent?: RootCloseEvent;
}
declare const Overlay: React.ForwardRefExoticComponent<OverlayProps & React.RefAttributes<HTMLElement>>;
export default Overlay;
