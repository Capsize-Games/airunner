import * as React from 'react';
export interface ToastContextType {
    onClose?: (e?: React.MouseEvent | React.KeyboardEvent) => void;
}
declare const ToastContext: React.Context<ToastContextType>;
export default ToastContext;
