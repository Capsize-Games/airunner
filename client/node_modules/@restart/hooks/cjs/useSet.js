"use strict";

exports.__esModule = true;
exports.default = exports.ObservableSet = void 0;
var _useForceUpdate = _interopRequireDefault(require("./useForceUpdate"));
var _useStableMemo = _interopRequireDefault(require("./useStableMemo"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
class ObservableSet extends Set {
  constructor(listener, init) {
    super(init);
    this.listener = listener;
  }
  add(value) {
    super.add(value);
    // When initializing the Set, the base Set calls this.add() before the
    // listener is assigned so it will be undefined
    if (this.listener) this.listener(this);
    return this;
  }
  delete(value) {
    const result = super.delete(value);
    this.listener(this);
    return result;
  }
  clear() {
    super.clear();
    this.listener(this);
  }
}

/**
 * Create and return a [Set](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set) that triggers rerenders when it's updated.
 *
 * ```ts
 * const ids = useSet<number>([1,2,3,4]);
 *
 * return (
 *  <>
 *    {Array.from(ids, id => (
 *      <div>
 *        id: {id}. <button onClick={() => ids.delete(id)}>X</button>
 *      </div>
 *    )}
 *  </>
 * )
 * ```
 *
 * @param init initial Set values
 */
exports.ObservableSet = ObservableSet;
function useSet(init) {
  const forceUpdate = (0, _useForceUpdate.default)();
  return (0, _useStableMemo.default)(() => new ObservableSet(forceUpdate, init), []);
}
var _default = useSet;
exports.default = _default;