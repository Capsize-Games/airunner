import { UseDebouncedCallbackOptions } from './useDebouncedCallback';
export type UseDebouncedValueOptions = UseDebouncedCallbackOptions & {
    isEqual?: (a: any, b: any) => boolean;
};
/**
 * Debounce a value change by a specified number of milliseconds. Useful
 * when you want need to trigger a change based on a value change, but want
 * to defer changes until the changes reach some level of infrequency.
 *
 * @param value
 * @param waitOrOptions
 * @returns
 */
declare function useDebouncedValue<TValue>(value: TValue, waitOrOptions?: number | UseDebouncedValueOptions): TValue;
export default useDebouncedValue;
