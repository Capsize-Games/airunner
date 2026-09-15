import PropTypes from 'prop-types';
export type ResponsiveUtilityValue<T> = T | {
    xs?: T;
    sm?: T;
    md?: T;
    lg?: T;
    xl?: T;
    xxl?: T;
};
export declare function responsivePropType(propType: any): PropTypes.Requireable<any>;
export default function createUtilityClassName(utilityValues: Record<string, ResponsiveUtilityValue<unknown>>, breakpoints?: string[], minBreakpoint?: string): string[];
