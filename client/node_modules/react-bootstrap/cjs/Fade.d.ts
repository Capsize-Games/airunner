import * as React from 'react';
import Transition from 'react-transition-group/Transition';
import { TransitionCallbacks } from '@restart/ui/types';
export interface FadeProps extends TransitionCallbacks {
    className?: string;
    in?: boolean;
    mountOnEnter?: boolean;
    unmountOnExit?: boolean;
    appear?: boolean;
    timeout?: number;
    children: React.ReactElement;
    transitionClasses?: Record<string, string>;
}
declare const Fade: React.ForwardRefExoticComponent<FadeProps & React.RefAttributes<Transition<any>>>;
export default Fade;
