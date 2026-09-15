import * as React from 'react';
export declare function isEscKey(e: KeyboardEvent): boolean;
export declare function getReactVersion(): {
    major: number;
    minor: number;
    patch: number;
};
export declare function getChildRef(element?: React.ReactElement | ((...args: any[]) => React.ReactNode) | null): React.Ref<any> | null;
