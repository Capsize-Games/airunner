import * as React from 'react';
import { CloseButtonVariant } from './CloseButton';
export interface AbstractModalHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
    closeLabel?: string;
    closeVariant?: CloseButtonVariant;
    closeButton?: boolean;
    onHide?: () => void;
}
declare const AbstractModalHeader: React.ForwardRefExoticComponent<AbstractModalHeaderProps & React.RefAttributes<HTMLDivElement>>;
export default AbstractModalHeader;
