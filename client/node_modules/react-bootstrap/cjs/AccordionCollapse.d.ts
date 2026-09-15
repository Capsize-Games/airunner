import { CollapseProps } from './Collapse';
import { BsPrefixRefForwardingComponent, BsPrefixProps } from './helpers';
export interface AccordionCollapseProps extends BsPrefixProps, CollapseProps {
    eventKey: string;
    /** @default 'accordion-collapse' */
    bsPrefix?: string;
}
/**
 * This component accepts all of [`Collapse`'s props](/docs/utilities/transitions#collapse-1).
 */
declare const AccordionCollapse: BsPrefixRefForwardingComponent<'div', AccordionCollapseProps>;
export default AccordionCollapse;
