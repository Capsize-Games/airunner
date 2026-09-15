import * as React from 'react';
import { WaypointOptions, WaypointEvent, Position } from './useWaypoint';
export { Position };
export type { WaypointEvent };
export interface WaypointProps extends WaypointOptions {
    renderComponent?: (ref: React.RefCallback<any>) => React.ReactElement;
    /**
     * The callback fired when a waypoint's position is updated. This generally
     * fires as a waypoint enters or exits the viewport but will also be called
     * on mount.
     */
    onPositionChange: (details: WaypointEvent, entry: IntersectionObserverEntry) => void;
}
/**
 * A component that tracks when it enters or leaves the viewport. Implemented
 * using IntersectionObserver, polyfill may be required for older browsers.
 */
declare function Waypoint({ renderComponent, onPositionChange, ...options }: WaypointProps): React.ReactElement<any, string | React.JSXElementConstructor<any>>;
export default Waypoint;
