import React from 'react';
import { TransitionComponent, TransitionProps } from './types';
export interface TransitionFunctionOptions {
    in: boolean;
    element: HTMLElement;
    initial: boolean;
    isStale: () => boolean;
}
export type TransitionHandler = (options: TransitionFunctionOptions) => void | Promise<void>;
export interface UseTransitionOptions {
    in: boolean;
    onTransition: TransitionHandler;
    initial?: boolean;
}
export declare function useTransition({ in: inProp, onTransition, }: UseTransitionOptions): React.RefObject<HTMLElement>;
export interface ImperativeTransitionProps extends TransitionProps {
    transition: TransitionHandler;
    appear: true;
    mountOnEnter: true;
    unmountOnExit: true;
}
/**
 * Adapts an imperative transition function to a subset of the RTG `<Transition>` component API.
 *
 * ImperativeTransition does not support mounting options or `appear` at the moment, meaning
 * that it always acts like: `mountOnEnter={true} unmountOnExit={true} appear={true}`
 */
export default function ImperativeTransition({ children, in: inProp, onExited, onEntered, transition, }: ImperativeTransitionProps): React.ReactElement<any, string | React.JSXElementConstructor<any>> | null;
export declare function renderTransition(component: TransitionComponent | undefined, runTransition: TransitionHandler | undefined, props: TransitionProps & Omit<ImperativeTransitionProps, 'transition'>): React.JSX.Element;
