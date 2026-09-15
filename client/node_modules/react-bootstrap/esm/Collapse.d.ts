import React from 'react';
import Transition from 'react-transition-group/Transition';
import { TransitionCallbacks } from '@restart/ui/types';
type Dimension = 'height' | 'width';
export interface CollapseProps extends TransitionCallbacks, Pick<React.HTMLAttributes<HTMLElement>, 'role'> {
    className?: string;
    in?: boolean;
    mountOnEnter?: boolean;
    unmountOnExit?: boolean;
    appear?: boolean;
    timeout?: number;
    dimension?: Dimension | (() => Dimension);
    getDimensionValue?: (dimension: Dimension, element: HTMLElement) => number;
    children: React.ReactElement;
}
declare const Collapse: React.ForwardRefExoticComponent<CollapseProps & React.RefAttributes<Transition<any>>>;
export default Collapse;
