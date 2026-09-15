import * as React from 'react';
import { OverlayChildren, OverlayProps } from './Overlay';
import { Placement } from './types';
export type OverlayTriggerType = 'hover' | 'click' | 'focus';
export type OverlayDelay = number | {
    show: number;
    hide: number;
};
export type OverlayInjectedProps = {
    onFocus?: (...args: any[]) => any;
};
export type OverlayTriggerRenderProps = OverlayInjectedProps & {
    ref: React.Ref<any>;
};
export interface OverlayTriggerProps extends Omit<OverlayProps, 'children' | 'target'> {
    children: React.ReactElement | ((props: OverlayTriggerRenderProps) => React.ReactNode);
    trigger?: OverlayTriggerType | OverlayTriggerType[];
    delay?: OverlayDelay;
    show?: boolean;
    defaultShow?: boolean;
    onToggle?: (nextShow: boolean) => void;
    flip?: boolean;
    overlay: OverlayChildren;
    target?: never;
    onHide?: never;
    placement?: Placement;
}
declare const OverlayTrigger: React.FC<OverlayTriggerProps>;
export default OverlayTrigger;
