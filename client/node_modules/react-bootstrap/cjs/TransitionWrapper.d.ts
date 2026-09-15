import React from 'react';
import Transition, { TransitionProps, TransitionStatus } from 'react-transition-group/Transition';
export type TransitionWrapperProps = TransitionProps & {
    childRef?: React.Ref<unknown>;
    children: React.ReactElement | ((status: TransitionStatus, props: Record<string, unknown>) => React.ReactNode);
};
declare const TransitionWrapper: React.ForwardRefExoticComponent<(Omit<import("react-transition-group/Transition").TimeoutProps<undefined> & {
    childRef?: React.Ref<unknown>;
    children: React.ReactElement | ((status: TransitionStatus, props: Record<string, unknown>) => React.ReactNode);
}, "ref"> | Omit<import("react-transition-group/Transition").EndListenerProps<undefined> & {
    childRef?: React.Ref<unknown>;
    children: React.ReactElement | ((status: TransitionStatus, props: Record<string, unknown>) => React.ReactNode);
}, "ref">) & React.RefAttributes<Transition<any>>>;
export default TransitionWrapper;
