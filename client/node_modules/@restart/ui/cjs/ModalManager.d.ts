export interface ModalInstance {
    dialog: Element;
    backdrop: Element;
}
export interface ModalManagerOptions {
    ownerDocument?: Document;
    handleContainerOverflow?: boolean;
    isRTL?: boolean;
}
export type ContainerState = {
    scrollBarWidth: number;
    style: Record<string, any>;
    [key: string]: any;
};
export declare const OPEN_DATA_ATTRIBUTE: "data-rr-ui-modal-open";
/**
 * Manages a stack of Modals as well as ensuring
 * body scrolling is is disabled and padding accounted for
 */
declare class ModalManager {
    readonly handleContainerOverflow: boolean;
    readonly isRTL: boolean;
    readonly modals: ModalInstance[];
    protected state: ContainerState;
    protected ownerDocument: Document | undefined;
    constructor({ ownerDocument, handleContainerOverflow, isRTL, }?: ModalManagerOptions);
    getScrollbarWidth(): number;
    getElement(): HTMLElement;
    setModalAttributes(_modal: ModalInstance): void;
    removeModalAttributes(_modal: ModalInstance): void;
    setContainerStyle(containerState: ContainerState): void;
    reset(): void;
    removeContainerStyle(containerState: ContainerState): void;
    add(modal: ModalInstance): number;
    remove(modal: ModalInstance): void;
    isTopModal(modal: ModalInstance): boolean;
}
export default ModalManager;
