export interface WaypointEvent {
    position: Position;
    previousPosition: Position | null;
}
export interface Rect {
    top?: number;
    bottom?: number;
    left?: number;
    right?: number;
}
export type WaypointCallback = (details: WaypointEvent, entry: IntersectionObserverEntry, observer: IntersectionObserver) => void;
export type RootElement = Element | Document | null | undefined;
/** Accepts all options an IntersectionObserver accepts */
export interface WaypointOptions extends Omit<IntersectionObserverInit, 'rootMargin' | 'root'> {
    /**
     * The "root" element to observe. This should be the scrollable view your waypoint
     * is rendered into. Accepts a DOM element, a function that returns a DOM element, `null`
     * indicating that the root is not ready yet, or the string "scrollParent" to
     * have the waypoint calculate the scroll parent itself.
     */
    root?: RootElement | 'scrollParent' | ((element: Element) => RootElement);
    /**
     * A valid CSS `margin` property or object containing the specific "top", "left", etc properties.
     * The root margin functionally adjusts the "size" of the viewport when considering the waypoint's
     * position. A positive margin will cause the waypoint to "enter" the waypoint early while a
     * negative margin will have the opposite effect.
     */
    rootMargin?: string | Rect;
    /**
     * Set the direction of the scroll to consider when tracking the waypoint's position
     */
    scrollDirection?: 'vertical' | 'horizontal';
}
export declare enum Position {
    UNKNOWN = 0,
    BEFORE = 1,
    INSIDE = 2,
    AFTER = 3
}
declare function useWaypoint(element: Element | null, callback: WaypointCallback, options?: WaypointOptions): void;
export default useWaypoint;
