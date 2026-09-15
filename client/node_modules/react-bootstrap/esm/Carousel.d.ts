import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export type CarouselVariant = 'dark' | string;
export interface CarouselRef {
    element?: HTMLElement;
    prev: (e?: React.SyntheticEvent) => void;
    next: (e?: React.SyntheticEvent) => void;
}
export interface CarouselProps extends BsPrefixProps, Omit<React.HTMLAttributes<HTMLElement>, 'onSelect'> {
    slide?: boolean;
    fade?: boolean;
    controls?: boolean;
    indicators?: boolean;
    indicatorLabels?: string[];
    activeIndex?: number;
    onSelect?: (eventKey: number, event: Record<string, unknown> | null) => void;
    defaultActiveIndex?: number;
    onSlide?: (eventKey: number, direction: 'start' | 'end') => void;
    onSlid?: (eventKey: number, direction: 'start' | 'end') => void;
    interval?: number | null;
    keyboard?: boolean;
    pause?: 'hover' | false;
    wrap?: boolean;
    touch?: boolean;
    prevIcon?: React.ReactNode;
    prevLabel?: React.ReactNode;
    nextIcon?: React.ReactNode;
    nextLabel?: React.ReactNode;
    variant?: CarouselVariant;
    ref?: React.Ref<CarouselRef> | React.MutableRefObject<CarouselRef | undefined>;
}
declare const _default: BsPrefixRefForwardingComponent<"div", CarouselProps> & {
    Caption: BsPrefixRefForwardingComponent<"div", import("./CarouselCaption").CarouselCaptionProps>;
    Item: BsPrefixRefForwardingComponent<"div", import("./CarouselItem").CarouselItemProps>;
};
export default _default;
