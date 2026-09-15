import * as React from 'react';
import { EventKey, TransitionCallbacks } from '@restart/ui/types';
import { BsPrefixProps, BsPrefixRefForwardingComponent, TransitionType } from './helpers';
export interface TabPaneProps extends TransitionCallbacks, BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    eventKey?: EventKey;
    active?: boolean;
    transition?: TransitionType;
    mountOnEnter?: boolean;
    unmountOnExit?: boolean;
}
declare const TabPane: BsPrefixRefForwardingComponent<'div', TabPaneProps>;
export default TabPane;
