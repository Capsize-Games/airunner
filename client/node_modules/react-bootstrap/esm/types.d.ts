import PropTypes from 'prop-types';
import { State, UsePopperOptions } from '@restart/ui/usePopper';
export type Variant = 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info' | 'dark' | 'light' | (string & {});
export type ButtonVariant = Variant | 'link' | 'outline-primary' | 'outline-secondary' | 'outline-success' | 'outline-danger' | 'outline-warning' | 'outline-info' | 'outline-dark' | 'outline-light';
export type Color = 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info' | 'dark' | 'light' | 'white' | 'muted' | (string & {});
export type Placement = import('@restart/ui/usePopper').Placement;
export type AlignDirection = 'start' | 'end';
export type ResponsiveAlignProp = {
    sm: AlignDirection;
} | {
    md: AlignDirection;
} | {
    lg: AlignDirection;
} | {
    xl: AlignDirection;
} | {
    xxl: AlignDirection;
} | Record<string, AlignDirection>;
export type AlignType = AlignDirection | ResponsiveAlignProp;
export declare const alignPropType: PropTypes.Requireable<NonNullable<object | AlignDirection | null | undefined>>;
export type RootCloseEvent = 'click' | 'mousedown';
export type GapValue = 0 | 1 | 2 | 3 | 4 | 5 | number;
export interface PopperRef {
    state: State | undefined;
    outOfBoundaries: boolean;
    placement: Placement | undefined;
    scheduleUpdate?: () => void;
    strategy: UsePopperOptions['strategy'];
}
