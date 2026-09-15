import * as React from 'react';
import type { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface AlertLinkProps extends BsPrefixProps, React.AnchorHTMLAttributes<HTMLElement> {
}
declare const AlertLink: BsPrefixRefForwardingComponent<'a', AlertLinkProps>;
export default AlertLink;
