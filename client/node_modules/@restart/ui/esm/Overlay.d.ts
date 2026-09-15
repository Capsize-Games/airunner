import * as React from 'react';
import { Offset, Placement, UsePopperOptions, UsePopperState, VirtualElement } from './usePopper';
import { RootCloseOptions } from './useRootClose';
import { DOMContainer } from './useWaitForDOMRef';
import { TransitionCallbacks, TransitionComponent } from './types';
import { TransitionHandler } from './ImperativeTransition';
export interface OverlayArrowProps extends Record<string, any> {
    ref: React.RefCallback<HTMLElement>;
    style: React.CSSProperties;
}
export interface OverlayMetadata {
    show: boolean;
    placement: Placement | undefined;
    popper: UsePopperState | null;
    arrowProps: Partial<OverlayArrowProps>;
}
export interface OverlayInjectedProps extends Record<string, any> {
    ref: React.RefCallback<HTMLElement>;
    style: React.CSSProperties;
    'aria-labelledby'?: string;
}
export interface OverlayProps extends TransitionCallbacks {
    /**
     * Enables the Popper.js `flip` modifier, allowing the Overlay to
     * automatically adjust it's placement in case of overlap with the viewport or toggle.
     * Refer to the [flip docs](https://popper.js.org/popper-documentation.html#modifiers..flip.enabled) for more info
     */
    flip?: boolean;
    /** Specify where the overlay element is positioned in relation to the target element */
    placement?: Placement;
    /**
     * Control offset of the overlay to the reference element.
     * A convenience shortcut to setting `popperConfig.modfiers.offset`
     */
    offset?: Offset;
    /**
     * Control how much space there is between the edge of the boundary element and overlay.
     * A convenience shortcut to setting `popperConfig.modfiers.preventOverflow.padding`
     */
    containerPadding?: number;
    /**
     * A set of popper options and props passed directly to react-popper's Popper component.
     */
    popperConfig?: Omit<UsePopperOptions, 'placement'>;
    /**
     * A DOM Element, [Virtual Element](https://popper.js.org/docs/v2/virtual-elements/), Ref to an element, or
     * function that returns either. The `target` element is where the overlay is positioned relative to.
     */
    container?: DOMContainer;
    /**
     * A DOM Element, Ref to an element, or function that returns either. The `target` element is where
     * the overlay is positioned relative to.
     */
    target: DOMContainer<HTMLElement | VirtualElement>;
    /**
     * Set the visibility of the Overlay
     */
    show?: boolean;
    /**
     * A `react-transition-group` `<Transition/>` component
     * used to animate the overlay as it changes visibility.
     */
    transition?: TransitionComponent;
    /**
     * A transition handler, called with the `show` state and overlay element.
     * Should return a promise when the transition is complete
     */
    runTransition?: TransitionHandler;
    /**
     * A Callback fired by the Overlay when it wishes to be hidden.
     *
     * __required__ when `rootClose` is `true`.
     *
     * @type func
     */
    onHide?: (e: Event) => void;
    /**
     * Specify whether the overlay should trigger `onHide` when the user clicks outside the overlay
     */
    rootClose?: boolean;
    /**
     * Specify disabled for disable RootCloseWrapper
     */
    rootCloseDisabled?: boolean;
    /**
     * Specify event for toggling overlay
     */
    rootCloseEvent?: RootCloseOptions['clickTrigger'];
    /**
     * A render prop that returns an overlay element.
     */
    children: (props: OverlayInjectedProps, meta: OverlayMetadata) => React.ReactNode;
}
/**
 * Built on top of `Popper.js`, the overlay component is
 * great for custom tooltip overlays.
 */
declare const Overlay: React.ForwardRefExoticComponent<OverlayProps & React.RefAttributes<HTMLElement>>;
export default Overlay;
