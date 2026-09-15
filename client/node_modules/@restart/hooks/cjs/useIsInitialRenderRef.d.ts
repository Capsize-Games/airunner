/// <reference types="react" />
/**
 * Returns ref that is `true` on the initial render and `false` on subsequent renders. It
 * is StrictMode safe, so will reset correctly if the component is unmounted and remounted.
 *
 * This hook *must* be used before any effects that read it's value to be accurate.
 */
export default function useIsInitialRenderRef(): import("react").MutableRefObject<boolean>;
