import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
type NumberAttr = number | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' | '10' | '11' | '12';
type ColOrderNumber = number | '1' | '2' | '3' | '4' | '5';
type ColOrder = ColOrderNumber | 'first' | 'last';
type ColSize = boolean | 'auto' | NumberAttr;
type ColSpec = ColSize | {
    span?: ColSize | null;
    offset?: NumberAttr;
    order?: ColOrder;
};
export interface ColProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    xs?: ColSpec;
    sm?: ColSpec;
    md?: ColSpec;
    lg?: ColSpec;
    xl?: ColSpec;
    xxl?: ColSpec;
    [key: string]: any;
}
export interface UseColMetadata {
    as?: React.ElementType;
    bsPrefix: string;
    spans: string[];
}
export declare function useCol({ as, bsPrefix, className, ...props }: ColProps): [any, UseColMetadata];
declare const Col: BsPrefixRefForwardingComponent<'div', ColProps>;
export default Col;
