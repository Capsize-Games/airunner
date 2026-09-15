export interface UseDebouncedCallbackOptions {
    wait: number;
    leading?: boolean;
    trailing?: boolean;
    maxWait?: number;
}
export interface UseDebouncedCallbackOptionsLeading extends UseDebouncedCallbackOptions {
    leading: true;
}
/**
 * Creates a debounced function that will invoke the input function after the
 * specified wait.
 *
 * > Heads up! debounced functions are not pure since they are called in a timeout
 * > Don't call them inside render.
 *
 * @param fn a function that will be debounced
 * @param waitOrOptions a wait in milliseconds or a debounce configuration
 */
declare function useDebouncedCallback<TCallback extends (...args: any[]) => any>(fn: TCallback, options: UseDebouncedCallbackOptionsLeading): (...args: Parameters<TCallback>) => ReturnType<TCallback>;
/**
 * Creates a debounced function that will invoke the input function after the
 * specified wait.
 *
 * > Heads up! debounced functions are not pure since they are called in a timeout
 * > Don't call them inside render.
 *
 * @param fn a function that will be debounced
 * @param waitOrOptions a wait in milliseconds or a debounce configuration
 */
declare function useDebouncedCallback<TCallback extends (...args: any[]) => any>(fn: TCallback, waitOrOptions: number | UseDebouncedCallbackOptions): (...args: Parameters<TCallback>) => ReturnType<TCallback> | undefined;
export default useDebouncedCallback;
