"use strict";

exports.__esModule = true;
exports.default = exports.ObservableMap = void 0;
var _useForceUpdate = _interopRequireDefault(require("./useForceUpdate"));
var _useStableMemo = _interopRequireDefault(require("./useStableMemo"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
class ObservableMap extends Map {
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
exports.ObservableMap = ObservableMap;
function useMap(init) {
  const forceUpdate = (0, _useForceUpdate.default)();
  return (0, _useStableMemo.default)(() => new ObservableMap(forceUpdate, init), []);
}
var _default = useMap;
exports.default = _default;