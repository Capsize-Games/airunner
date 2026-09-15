/// <reference types="react" />
import { ClickOutsideOptions } from './useClickOutside';
export interface RootCloseOptions extends ClickOutsideOptions {
    disabled?: boolean;
}
/**
 * The `useRootClose` hook registers your callback on the document
 * when rendered. Powers the `<Overlay/>` component. This is used achieve modal
 * style behavior where your callback is triggered when the user tries to
 * interact with the rest of the document or hits the `esc` key.
 *
 * @param {Ref<HTMLElement>| HTMLElement} ref  The element boundary
 * @param {function} onRootClose
 * @param {object=}  options
 * @param {boolean=} options.disabled
 * @param {string=}  options.clickTrigger The DOM event name (click, mousedown, etc) to attach listeners on
 */
declare function useRootClose(ref: React.RefObject<Element> | Element | null | undefined, onRootClose: (e: Event) => void, { disabled, clickTrigger }?: RootCloseOptions): void;
export default useRootClose;
