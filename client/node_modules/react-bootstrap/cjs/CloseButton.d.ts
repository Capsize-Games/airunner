import * as React from 'react';
export type CloseButtonVariant = 'white' | string;
export interface CloseButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: CloseButtonVariant;
}
declare const CloseButton: React.ForwardRefExoticComponent<CloseButtonProps & React.RefAttributes<HTMLButtonElement>>;
export default CloseButton;
