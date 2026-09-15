import * as React from 'react';
import { TransitionCallbacks } from '@restart/ui/types';
import { BsPrefixRefForwardingComponent, BsPrefixProps } from './helpers';
export interface AccordionBodyProps extends BsPrefixProps, TransitionCallbacks, React.HTMLAttributes<HTMLElement> {
}
declare const AccordionBody: BsPrefixRefForwardingComponent<'div', AccordionBodyProps>;
export default AccordionBody;
