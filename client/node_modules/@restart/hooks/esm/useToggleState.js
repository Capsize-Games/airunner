import { useReducer } from 'react';

/**
 * Create a state setter pair for a boolean value that can be "switched".
 * Unlike `useState(false)`, `useToggleState` will automatically flip the state
 * value when its setter is called with no argument.
 *
 * @param initialState The initial boolean value
 * @returns A tuple of the current state and a setter
 *
 * ```jsx
 * const [show, toggleShow] = useToggleState(false)
 *
 * return (
 *   <>
 *     <button onClick={() => toggleShow()}>
 *       Toggle
 *     <button>
 *
 *     {show && <strong>Now you can see me</strong>}
 *   </>
 * )
 *
 * ```
 */
export default function useToggleState(initialState = false) {
  return useReducer((state, action) => action == null ? !state : action, initialState);
}