import { Dispatch, SetStateAction } from 'react';
import { UseDebouncedCallbackOptions } from './useDebouncedCallback';
/**
 * Similar to `useState`, except the setter function is debounced by
 * the specified delay. Unlike `useState`, the returned setter is not "pure" having
 * the side effect of scheduling an update in a timeout, which makes it unsafe to call
 * inside of the component render phase.
 *
 * ```ts
 * const [value, setValue] = useDebouncedState('test', 500)
 *
 * setValue('test2')
 * ```
 *
 * @param initialState initial state value
 * @param delayOrOptions The milliseconds delay before a new value is set, or options object
 */
export default function useDebouncedState<T>(initialState: T | (() => T), delayOrOptions: number | UseDebouncedCallbackOptions): [T, Dispatch<SetStateAction<T>>];
