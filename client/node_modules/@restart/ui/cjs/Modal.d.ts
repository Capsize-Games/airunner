import * as React from 'react';
import ModalManager from './ModalManager';
import { DOMContainer } from './useWaitForDOMRef';
import { TransitionCallbacks } from './types';
import { TransitionHandler } from './ImperativeTransition';
export interface ModalTransitionProps extends TransitionCallbacks {
    in: boolean;
    appear?: boolean;
    unmountOnExit?: boolean;
    children: React.ReactElement;
}
export type ModalTransitionComponent = React.ComponentType<ModalTransitionProps>;
export interface RenderModalDialogProps {
    style: React.CSSProperties | undefined;
    className: string | undefined;
    tabIndex: number;
    role: string;
    ref: React.RefCallback<Element>;
    'aria-modal': boolean | undefined;
}
export interface RenderModalBackdropProps {
    ref: React.RefCallback<Element>;
    onClick: (event: React.SyntheticEvent) => void;
}
export interface BaseModalProps extends TransitionCallbacks {
    children?: React.ReactElement;
    role?: string;
    style?: React.CSSProperties;
    className?: string;
    /**
     * Set the visibility of the Modal
     */
    show?: boolean;
    /**
     * A DOM element, a `ref` to an element, or function that returns either. The Modal is appended to it's `container` element.
     *
     */
    container?: DOMContainer;
    /**
     * A callback fired when the Modal is opening.
     */
    onShow?: () => void;
    /**
     * A callback fired when either the backdrop is clicked, or the escape key is pressed.
     *
     * The `onHide` callback only signals intent from the Modal,
     * you must actually set the `show` prop to `false` for the Modal to close.
     */
    onHide?: () => void;
    /**
     * A ModalManager instance used to track and manage the state of open
     * Modals. Useful when customizing how modals interact within a container
     */
    manager?: ModalManager;
    /**
     * Include a backdrop component. A `static`backdrop
     * will not trigger a Modal onHide when clicked.
     */
    backdrop?: true | false | 'static';
    /**
     * A function that returns the dialog component. Useful for custom
     * rendering. **Note:** the component should make sure to apply the provided ref.
     *
     * ```js static
     * renderDialog={props => <MyDialog {...props} />}
     * ```
     */
    renderDialog?: (props: RenderModalDialogProps) => React.ReactNode;
    /**
     * A function that returns a backdrop component. Useful for custom
     * backdrop rendering.
     *
     * ```js
     *  renderBackdrop={props => <MyBackdrop {...props} />}
     * ```
     */
    renderBackdrop?: (props: RenderModalBackdropProps) => React.ReactNode;
    /**
     * A callback fired when the escape key, if specified in `keyboard`, is pressed.
     *
     * If preventDefault() is called on the keyboard event, closing the modal will be cancelled.
     */
    onEscapeKeyDown?: (e: KeyboardEvent) => void;
    /**
     * A callback fired when the backdrop, if specified, is clicked.
     */
    onBackdropClick?: (e: React.SyntheticEvent) => void;
    /**
     * Close the modal when escape key is pressed
     */
    keyboard?: boolean;
    /**
     * A `react-transition-group` `<Transition/>` component used
     * to control animations for the dialog component.
     */
    transition?: ModalTransitionComponent;
    /**
     * A transition handler, called with the `show` state and dialog element.
     * Should return a promise when the transition is complete
     */
    runTransition?: TransitionHandler;
    /**
     * A `react-transition-group` `<Transition/>` component used
     * to control animations for the backdrop components.
     */
    backdropTransition?: ModalTransitionComponent;
    /**
     * A transition handler, called with the `show` state and backdrop element.
     * Should return a promise when the transition is complete
     */
    runBackdropTransition?: TransitionHandler;
    /**
     * When `true` The modal will automatically shift focus to itself when it opens, and
     * replace it to the last focused element when it closes. This also
     * works correctly with any Modal children that have the `autoFocus` prop.
     *
     * Generally this should never be set to `false` as it makes the Modal less
     * accessible to assistive technologies, like screen readers.
     */
    autoFocus?: boolean;
    /**
     * When `true` The modal will prevent focus from leaving the Modal while open.
     *
     * Generally this should never be set to `false` as it makes the Modal less
     * accessible to assistive technologies, like screen readers.
     */
    enforceFocus?: boolean;
    /**
     * When `true` The modal will restore focus to previously focused element once
     * modal is hidden
     */
    restoreFocus?: boolean;
    /**
     * Options passed to focus function when `restoreFocus` is set to `true`
     *
     * @link  https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus#Parameters
     */
    restoreFocusOptions?: {
        preventScroll: boolean;
    };
}
export interface ModalProps extends BaseModalProps {
    [other: string]: any;
}
export interface ModalHandle {
    dialog: HTMLElement | null;
    backdrop: HTMLElement | null;
    isTopModal: () => boolean;
}
declare const _default: React.ForwardRefExoticComponent<ModalProps & React.RefAttributes<ModalHandle>> & {
    Manager: typeof ModalManager;
};
export default _default;
