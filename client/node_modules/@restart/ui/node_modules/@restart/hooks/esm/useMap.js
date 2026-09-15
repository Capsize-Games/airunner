import useForceUpdate from './useForceUpdate';
import useStableMemo from './useStableMemo';
export class ObservableMap extends Map {
  constructor(listener, init) {
    super(init);
    this.listener = listener;
  }
  set(key, value) {
    super.set(key, value);
    // When initializing the Map, the base Map calls this.set() before the
    // listener is assigned so it will be undefined
    if (this.listener) this.listener(this);
    return this;
  }
  delete(key) {
    let result = super.delete(key);
    this.listener(this);
    return result;
  }
  clear() {
    super.clear();
    this.listener(this);
  }
}

/**
 * Create and return a [Map](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map) that triggers rerenders when it's updated.
 *
 * ```tsx
 * const customerAges = useMap<number>([
 *  ['john', 24],
 *  ['betsy', 25]
 * ]);
 *
 * return (
 *  <>
 *    {Array.from(ids, ([name, age]) => (
 *      <div>
 *        {name}: {age}. <button onClick={() => ids.delete(name)}>X</button>
 *      </div>
 *    )}
 *  </>
 * )
 * ```
 *
 * @param init initial Map entries
 */
function useMap(init) {
  const forceUpdate = useForceUpdate();
  return useStableMemo(() => new ObservableMap(forceUpdate, init), []);
}
export default useMap;