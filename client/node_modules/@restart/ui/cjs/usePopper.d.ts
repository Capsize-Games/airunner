import * as Popper from '@popperjs/core';
export type Modifier<Name, Options extends Popper.Obj> = Popper.Modifier<Name, Options>;
export type Options = Popper.Options;
export type Instance = Popper.Instance;
export type Placement = Popper.Placement;
export type VirtualElement = Popper.VirtualElement;
export type State = Popper.State;
export type OffsetValue = [
    number | null | undefined,
    number | null | undefined
];
export type OffsetFunction = (details: {
    popper: Popper.Rect;
    reference: Popper.Rect;
    placement: Placement;
}) => OffsetValue;
export type Offset = OffsetFunction | OffsetValue;
export type ModifierMap = Record<string, Partial<Modifier<any, any>>>;
export type Modifiers = Popper.Options['modifiers'] | Record<string, Partial<Modifier<any, any>>>;
export type UsePopperOptions = Omit<Options, 'modifiers' | 'placement' | 'strategy'> & {
    enabled?: boolean;
    placement?: Options['placement'];
    strategy?: Options['strategy'];
    modifiers?: Options['modifiers'];
};
export interface UsePopperState {
    placement: Placement;
    update: () => void;
    forceUpdate: () => void;
    attributes: Record<string, Record<string, any>>;
    styles: Record<string, Partial<CSSStyleDeclaration>>;
    state?: State;
}
/**
 * Position an element relative some reference element using Popper.js
 *
 * @param referenceElement
 * @param popperElement
 * @param {object}      options
 * @param {object=}     options.modifiers Popper.js modifiers
 * @param {boolean=}    options.enabled toggle the popper functionality on/off
 * @param {string=}     options.placement The popper element placement relative to the reference element
 * @param {string=}     options.strategy the positioning strategy
 * @param {function=}   options.onCreate called when the popper is created
 * @param {function=}   options.onUpdate called when the popper is updated
 *
 * @returns {UsePopperState} The popper state
 */
declare function usePopper(referenceElement: VirtualElement | null | undefined, popperElement: HTMLElement | null | undefined, { enabled, placement, strategy, modifiers, ...config }?: UsePopperOptions): UsePopperState;
export default usePopper;
