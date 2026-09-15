/// <reference types="react" />
import { TransitionProps as RTGTransitionProps, TransitionStatus } from 'react-transition-group/Transition';
export type TransitionProps = RTGTransitionProps & {
    children: React.ReactElement | ((status: TransitionStatus, props: Record<string, unknown>) => React.ReactNode);
};
/**
 * Normalizes RTG transition callbacks with nodeRef to better support
 * strict mode.
 *
 * @param props Transition props.
 * @returns Normalized transition props.
 */
export default function useRTGTransitionProps({ onEnter, onEntering, onEntered, onExit, onExiting, onExited, addEndListener, children, ...props }: TransitionProps): {
    children: any;
    addEndListener?: ((param: any) => void) | undefined;
    onExited?: ((param: any) => void) | undefined;
    onExiting?: ((param: any) => void) | undefined;
    onExit?: ((param: any) => void) | undefined;
    onEntered?: ((param: any) => void) | undefined;
    onEntering?: ((param: any) => void) | undefined;
    onEnter?: ((param: any) => void) | undefined;
    nodeRef: import("react").RefObject<HTMLElement>;
    timeout: number | {
        appear?: number | undefined;
        enter?: number | undefined;
        exit?: number | undefined;
    };
    in?: boolean | undefined;
    mountOnEnter?: boolean | undefined;
    unmountOnExit?: boolean | undefined;
} | {
    children: any;
    addEndListener?: ((param: any) => void) | undefined;
    onExited?: ((param: any) => void) | undefined;
    onExiting?: ((param: any) => void) | undefined;
    onExit?: ((param: any) => void) | undefined;
    onEntered?: ((param: any) => void) | undefined;
    onEntering?: ((param: any) => void) | undefined;
    onEnter?: ((param: any) => void) | undefined;
    nodeRef: import("react").RefObject<HTMLElement>;
    timeout?: number | {
        appear?: number | undefined;
        enter?: number | undefined;
        exit?: number | undefined;
    } | undefined;
    in?: boolean | undefined;
    mountOnEnter?: boolean | undefined;
    unmountOnExit?: boolean | undefined;
};
