import * as React from 'react';
export type AccordionEventKey = string | string[] | null | undefined;
export declare type AccordionSelectCallback = (eventKey: AccordionEventKey, e: React.SyntheticEvent<unknown>) => void;
export interface AccordionContextValue {
    activeEventKey?: AccordionEventKey;
    onSelect?: AccordionSelectCallback;
    alwaysOpen?: boolean;
}
export declare function isAccordionItemSelected(activeEventKey: AccordionEventKey, eventKey: string): boolean;
declare const context: React.Context<AccordionContextValue>;
export default context;
