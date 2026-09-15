import * as React from 'react';
import type { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface CardLinkProps extends BsPrefixProps, React.AnchorHTMLAttributes<HTMLElement> {
}
declare const CardLink: BsPrefixRefForwardingComponent<'a', CardLinkProps>;
export default CardLink;
