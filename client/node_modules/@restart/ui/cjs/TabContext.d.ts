import * as React from 'react';
import { EventKey, SelectCallback, TransitionComponent } from './types';
export interface TabContextType {
    onSelect: SelectCallback;
    activeKey?: EventKey;
    transition?: TransitionComponent;
    mountOnEnter: boolean;
    unmountOnExit: boolean;
    getControlledId: (key: EventKey) => any;
    getControllerId: (key: EventKey) => any;
}
declare const TabContext: React.Context<TabContextType | null>;
export default TabContext;
