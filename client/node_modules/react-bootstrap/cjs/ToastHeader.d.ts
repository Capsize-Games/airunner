import * as React from 'react';
import { CloseButtonVariant } from './CloseButton';
import { BsPrefixOnlyProps } from './helpers';
export interface ToastHeaderProps extends BsPrefixOnlyProps, React.HTMLAttributes<HTMLDivElement> {
    closeLabel?: string;
    closeVariant?: CloseButtonVariant;
    closeButton?: boolean;
}
declare const ToastHeader: React.ForwardRefExoticComponent<ToastHeaderProps & React.RefAttributes<HTMLDivElement>>;
export default ToastHeader;
