import * as React from 'react';
export type EventKey = string | number;
export type IntrinsicElementTypes = keyof React.JSX.IntrinsicElements;
export type AssignPropsWithRef<Inner extends string | React.ComponentType<any>, P> = Omit<React.ComponentPropsWithRef<Inner extends React.ElementType ? Inner : never>, keyof P> & P;
export type { AssignPropsWithRef as AssignProps };
export type AssignPropsWithoutRef<Inner extends string | React.ComponentType<any>, P> = Omit<React.ComponentPropsWithoutRef<Inner extends React.ElementType ? Inner : never>, keyof P> & P;
export interface DynamicRefForwardingComponent<TInitial extends string | React.ComponentType<any>, P = {
    children?: React.ReactNode;
}> {
    <As extends string | React.ComponentType<any> = TInitial>(props: AssignPropsWithRef<As, {
        as?: As;
    } & P>, context?: any): React.ReactElement | null;
    propTypes?: any;
    contextTypes?: any;
    defaultProps?: Partial<P>;
    displayName?: string;
}
export interface DynamicFunctionComponent<TInitial extends string | React.ComponentType<any>, P = {
    children?: React.ReactNode;
}> {
    <As extends string | React.ComponentType<any> = TInitial>(props: AssignPropsWithoutRef<As, {
        as?: As;
    } & P>, context?: any): React.ReactElement | null;
    propTypes?: any;
    contextTypes?: any;
    defaultProps?: Partial<P>;
    displayName?: string;
}
export declare class DynamicComponent<As extends string | React.ComponentType<any>, P = unknown> extends React.Component<AssignPropsWithRef<As, {
    as?: As;
} & P>> {
}
export type DynamicComponentClass<As extends string | React.ComponentType<any>, P = unknown> = React.ComponentClass<AssignPropsWithRef<As, {
    as?: As;
} & P>>;
export type SelectCallback = (eventKey: string | null, e: React.SyntheticEvent<unknown>) => void;
export interface TransitionCallbacks {
    /**
     * Callback fired before the component transitions in
     */
    onEnter?(node: HTMLElement, isAppearing: boolean): any;
    /**
     * Callback fired as the component begins to transition in
     */
    onEntering?(node: HTMLElement, isAppearing: boolean): any;
    /**
     * Callback fired after the component finishes transitioning in
     */
    onEntered?(node: HTMLElement, isAppearing: boolean): any;
    /**
     * Callback fired right before the component transitions out
     */
    onExit?(node: HTMLElement): any;
    /**
     * Callback fired as the component begins to transition out
     */
    onExiting?(node: HTMLElement): any;
    /**
     * Callback fired after the component finishes transitioning out
     */
    onExited?(node: HTMLElement): any;
}
export interface TransitionProps extends TransitionCallbacks {
    in?: boolean;
    appear?: boolean;
    children: React.ReactElement;
    mountOnEnter?: boolean;
    unmountOnExit?: boolean;
}
export type TransitionComponent = React.ComponentType<TransitionProps>;
