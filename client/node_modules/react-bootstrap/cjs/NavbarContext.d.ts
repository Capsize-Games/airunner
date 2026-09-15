import * as React from 'react';
export interface NavbarContextType {
    onToggle: () => void;
    bsPrefix?: string;
    expanded: boolean;
    expand?: boolean | string | 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
}
declare const context: React.Context<NavbarContextType | null>;
export default context;
