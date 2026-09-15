import * as React from 'react';
import { OverlayArrowProps } from '@restart/ui/Overlay';
import { Placement, PopperRef } from './types';
import { BsPrefixProps } from './helpers';
export interface PopoverProps extends React.HTMLAttributes<HTMLDivElement>, BsPrefixProps {
    placement?: Placement;
    title?: string;
    arrowProps?: Partial<OverlayArrowProps>;
    body?: boolean;
    popper?: PopperRef;
    show?: boolean;
    hasDoneInitialMeasure?: boolean;
}
declare const _default: React.ForwardRefExoticComponent<PopoverProps & React.RefAttributes<HTMLDivElement>> & {
    Header: import("./helpers").BsPrefixRefForwardingComponent<"div", import("./PopoverHeader").PopoverHeaderProps>;
    Body: import("./helpers").BsPrefixRefForwardingComponent<"div", import("./PopoverBody").PopoverBodyProps>;
    POPPER_OFFSET: readonly [0, 8];
};
export default _default;
