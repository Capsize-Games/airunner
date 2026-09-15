import * as React from 'react';
export declare function isTrivialHref(href?: string): boolean;
export interface AnchorProps extends React.HTMLAttributes<HTMLElement> {
    href?: string;
    disabled?: boolean;
    role?: string;
    tabIndex?: number;
}
/**
 * An generic `<a>` component that covers a few A11y cases, ensuring that
 * cases where the `href` is missing or trivial like "#" are treated like buttons.
 */
declare const Anchor: React.ForwardRefExoticComponent<AnchorProps & React.RefAttributes<HTMLAnchorElement>>;
export default Anchor;
