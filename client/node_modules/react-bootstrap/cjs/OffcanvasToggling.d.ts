import * as React from 'react';
import Transition from 'react-transition-group/Transition';
import { TransitionCallbacks } from '@restart/ui/types';
import { BsPrefixOnlyProps } from './helpers';
export interface OffcanvasTogglingProps extends TransitionCallbacks, BsPrefixOnlyProps {
    className?: string;
    in?: boolean;
    mountOnEnter?: boolean;
    unmountOnExit?: boolean;
    appear?: boolean;
    timeout?: number;
    children: React.ReactElement;
}
declare const OffcanvasToggling: React.ForwardRefExoticComponent<OffcanvasTogglingProps & React.RefAttributes<Transition<any>>>;
export default OffcanvasToggling;
