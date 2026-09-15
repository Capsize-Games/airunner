import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { Color, Variant } from './types';
export interface BadgeProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    bg?: Variant;
    pill?: boolean;
    text?: Color;
}
declare const Badge: BsPrefixRefForwardingComponent<'span', BadgeProps>;
export default Badge;
