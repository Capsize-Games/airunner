import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
type EventHandler = React.EventHandler<React.SyntheticEvent>;
export interface AccordionButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, BsPrefixProps {
}
export declare function useAccordionButton(eventKey: string, onClick?: EventHandler): EventHandler;
declare const AccordionButton: BsPrefixRefForwardingComponent<'div', AccordionButtonProps>;
export default AccordionButton;
