import * as React from 'react';
import { AccordionSelectCallback, AccordionEventKey } from './AccordionContext';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface AccordionProps extends Omit<React.HTMLAttributes<HTMLElement>, 'onSelect'>, BsPrefixProps {
    activeKey?: AccordionEventKey;
    defaultActiveKey?: AccordionEventKey;
    onSelect?: AccordionSelectCallback;
    flush?: boolean;
    alwaysOpen?: boolean;
}
declare const _default: BsPrefixRefForwardingComponent<"div", AccordionProps> & {
    Button: BsPrefixRefForwardingComponent<"div", import("./AccordionButton").AccordionButtonProps>;
    Collapse: BsPrefixRefForwardingComponent<"div", import("./AccordionCollapse").AccordionCollapseProps>;
    Item: BsPrefixRefForwardingComponent<"div", import("./AccordionItem").AccordionItemProps>;
    Header: BsPrefixRefForwardingComponent<"h2", import("./AccordionHeader").AccordionHeaderProps>;
    Body: BsPrefixRefForwardingComponent<"div", import("./AccordionBody").AccordionBodyProps>;
};
export default _default;
