import * as React from 'react';
import { DOMContainer } from './useWaitForDOMRef';
export interface PortalProps {
    children: React.ReactElement;
    /**
     * A DOM element, Ref to an element, or function that returns either. The `container` will have the Portal children
     * appended to it.
     */
    container: DOMContainer;
    /**
     * Callback that is triggered when the portal content is rendered.
     */
    onRendered?: (element: any) => void;
}
/**
 * @public
 */
declare const Portal: {
    ({ container, children, onRendered }: PortalProps): React.JSX.Element | null;
    displayName: string;
};
export default Portal;
