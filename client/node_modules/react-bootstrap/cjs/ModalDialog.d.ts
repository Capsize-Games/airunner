import * as React from 'react';
import { BsPrefixProps } from './helpers';
export interface ModalDialogProps extends React.HTMLAttributes<HTMLDivElement>, BsPrefixProps {
    size?: 'sm' | 'lg' | 'xl';
    fullscreen?: true | string | 'sm-down' | 'md-down' | 'lg-down' | 'xl-down' | 'xxl-down';
    centered?: boolean;
    scrollable?: boolean;
    contentClassName?: string;
}
declare const ModalDialog: React.ForwardRefExoticComponent<ModalDialogProps & React.RefAttributes<HTMLDivElement>>;
export default ModalDialog;
