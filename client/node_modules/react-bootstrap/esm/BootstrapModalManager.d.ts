import ModalManager, { ContainerState, ModalManagerOptions } from '@restart/ui/ModalManager';
declare class BootstrapModalManager extends ModalManager {
    private adjustAndStore;
    private restore;
    setContainerStyle(containerState: ContainerState): void;
    removeContainerStyle(containerState: ContainerState): void;
}
export declare function getSharedManager(options?: ModalManagerOptions): BootstrapModalManager;
export default BootstrapModalManager;
