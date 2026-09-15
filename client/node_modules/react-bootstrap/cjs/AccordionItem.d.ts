import * as React from 'react';
import { BsPrefixRefForwardingComponent, BsPrefixProps } from './helpers';
export interface AccordionItemProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    eventKey: string;
}
declare const AccordionItem: BsPrefixRefForwardingComponent<'div', AccordionItemProps>;
export default AccordionItem;
