import * as React from 'react';
import { OverlayArrowProps } from '@restart/ui/Overlay';
import { Placement, PopperRef } from './types';
import { BsPrefixProps } from './helpers';
export interface TooltipProps extends React.HTMLAttributes<HTMLDivElement>, BsPrefixProps {
    placement?: Placement;
    arrowProps?: Partial<OverlayArrowProps>;
    show?: boolean;
    popper?: PopperRef;
    hasDoneInitialMeasure?: boolean;
}
declare const _default: React.ForwardRefExoticComponent<TooltipProps & React.RefAttributes<HTMLDivElement>> & {
    TOOLTIP_OFFSET: number[];
};
export default _default;
