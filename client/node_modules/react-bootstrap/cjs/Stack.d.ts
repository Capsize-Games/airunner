import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { GapValue } from './types';
import { ResponsiveUtilityValue } from './createUtilityClasses';
export type StackDirection = 'horizontal' | 'vertical';
export interface StackProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    direction?: StackDirection;
    gap?: ResponsiveUtilityValue<GapValue>;
}
declare const Stack: BsPrefixRefForwardingComponent<'span', StackProps>;
export default Stack;
