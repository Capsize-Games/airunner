import * as React from 'react';
import { CloseButtonVariant } from './CloseButton';
import { Variant } from './types';
import { TransitionType } from './helpers';
export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
    bsPrefix?: string;
    variant?: Variant;
    dismissible?: boolean;
    show?: boolean;
    onClose?: (a: any, b: any) => void;
    closeLabel?: string;
    closeVariant?: CloseButtonVariant;
    transition?: TransitionType;
}
declare const _default: React.ForwardRefExoticComponent<AlertProps & React.RefAttributes<HTMLDivElement>> & {
    Link: import("./helpers").BsPrefixRefForwardingComponent<"a", import("./AlertLink").AlertLinkProps>;
    Heading: import("./helpers").BsPrefixRefForwardingComponent<"div", import("./AlertHeading").AlertHeadingProps>;
};
export default _default;
