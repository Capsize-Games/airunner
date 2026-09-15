import * as React from 'react';
import { EventKey } from './types';
interface NavContextType {
    role?: string;
    activeKey: EventKey | null;
    getControlledId: (key: EventKey | null) => string;
    getControllerId: (key: EventKey | null) => string;
}
declare const NavContext: React.Context<NavContextType | null>;
export default NavContext;
