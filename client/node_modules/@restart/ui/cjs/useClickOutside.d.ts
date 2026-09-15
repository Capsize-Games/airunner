/// <reference types="react" />
export type MouseEvents = {
    [K in keyof GlobalEventHandlersEventMap]: GlobalEventHandlersEventMap[K] extends MouseEvent ? K : never;
}[keyof GlobalEventHandlersEventMap];
export declare const getRefTarget: (ref: React.RefObject<Element> | Element | null | undefined) => Element | null | undefined;
export interface ClickOutsideOptions {
    disabled?: boolean;
    clickTrigger?: MouseEvents;
}
/**
 * The `useClickOutside` hook registers your callback on the document that fires
 * when a pointer event is registered outside of the provided ref or element.
 *
 * @param {Ref<HTMLElement>| HTMLElement} ref  The element boundary
 * @param {function} onClickOutside
 * @param {object=}  options
 * @param {boolean=} options.disabled
 * @param {string=}  options.clickTrigger The DOM event name (click, mousedown, etc) to attach listeners on
 */
declare function useClickOutside(ref: React.RefObject<Element> | Element | null | undefined, onClickOutside?: (e: Event) => void, { disabled, clickTrigger }?: ClickOutsideOptions): void;
export default useClickOutside;
