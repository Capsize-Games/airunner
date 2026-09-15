import * as React from 'react';
import { AlignType } from './types';
export type DropDirection = 'up' | 'up-centered' | 'start' | 'end' | 'down' | 'down-centered';
export type DropdownContextValue = {
    align?: AlignType;
    drop?: DropDirection;
    isRTL?: boolean;
};
declare const DropdownContext: React.Context<DropdownContextValue>;
export default DropdownContext;
