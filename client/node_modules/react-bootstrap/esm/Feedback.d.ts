import * as React from 'react';
import { AsProp, BsPrefixRefForwardingComponent } from './helpers';
export type FeedbackType = 'valid' | 'invalid';
export interface FeedbackProps extends AsProp, React.HTMLAttributes<HTMLElement> {
    bsPrefix?: never;
    type?: FeedbackType;
    tooltip?: boolean;
}
declare const Feedback: BsPrefixRefForwardingComponent<'div', FeedbackProps>;
export default Feedback;
