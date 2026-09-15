/// <reference types="react" />
import { VirtualElement } from './usePopper';
export type DOMContainer<T extends HTMLElement | VirtualElement = HTMLElement> = T | React.RefObject<T | null> | null | (() => T | React.RefObject<T | null> | null);
export declare const resolveContainerRef: <T extends HTMLElement | import("@popperjs/core").VirtualElement>(ref: DOMContainer<T> | undefined, document?: Document) => HTMLBodyElement | T | null;
export default function useWaitForDOMRef<T extends HTMLElement | VirtualElement = HTMLElement>(ref: DOMContainer<T> | undefined, onResolved?: (element: T | HTMLBodyElement) => void): HTMLBodyElement | T | null;
