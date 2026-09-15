"use strict";

exports.__esModule = true;
exports.default = exports.Position = void 0;
var _useEventCallback = _interopRequireDefault(require("@restart/hooks/useEventCallback"));
var _useIntersectionObserver = _interopRequireDefault(require("@restart/hooks/useIntersectionObserver"));
var _react = require("react");
var _scrollParent = _interopRequireDefault(require("dom-helpers/scrollParent"));
function _interopRequireDefault(e) { return e && e.__esModule ? e : { default: e }; }
/** Accepts all options an IntersectionObserver accepts */
let Position = exports.Position = void 0;
(function (Position) {
  Position[Position["UNKNOWN"] = 0] = "UNKNOWN";
  Position[Position["BEFORE"] = 1] = "BEFORE";
  Position[Position["INSIDE"] = 2] = "INSIDE";
  Position[Position["AFTER"] = 3] = "AFTER";
})(Position || (exports.Position = Position = {}));
function toCss(margin) {
  if (!margin || typeof margin === 'string') return margin;
  const {
    top = 0,
    right = 0,
    bottom = 0,
    left = 0
  } = margin;
  return `${top}px ${right}px ${bottom}px ${left}px`;
}
const findRoot = el => (0, _scrollParent.default)(el, true);
function useWaypoint(element, callback, options = {}) {
  const {
    rootMargin,
    threshold,
    scrollDirection = 'vertical'
  } = options;
  let {
    root
  } = options;
  const handler = (0, _useEventCallback.default)(callback);
  const prevPositionRef = (0, _react.useRef)(null);
  if (root === 'scrollParent') {
    root = findRoot;
  }
  const scrollParent = (0, _react.useMemo)(() => element && typeof root === 'function' ? root(element) : null, [element, root]);
  let realRoot = typeof root === 'function' ? scrollParent : root;
  if (realRoot && realRoot.nodeType === document.DOCUMENT_NODE) {
    // explicit undefined means "use the viewport", instead of `null`
    // which means "no root yet". This works around a bug in safari
    // where document is not accepted in older versions,
    // or is accepted but doesn't work (as of v14)
    realRoot = undefined;
  }
  (0, _useIntersectionObserver.default)(
  // We change the meaning of explicit null to "not provided yet"
  // this is to allow easier synchronizing between element and roots derived
  // from it. Otherwise if the root updates later an observer will be created
  // for the document and then for the root
  element, ([entry], observer) => {
    var _entry$rootBounds, _entry$rootBounds2;
    if (!entry) return;
    const [start, end, point] = scrollDirection === 'vertical' ? ['top', 'bottom', 'y'] : ['left', 'right', 'x'];
    const {
      [point]: coord
    } = entry.boundingClientRect;
    const rootStart = ((_entry$rootBounds = entry.rootBounds) == null ? void 0 : _entry$rootBounds[start]) || 0;
    const rootEnd = ((_entry$rootBounds2 = entry.rootBounds) == null ? void 0 : _entry$rootBounds2[end]) || 0;

    // The position may remain UNKNOWN if the root
    // is 0 width/height or everything is hidden.
    let position = Position.UNKNOWN;
    if (entry.isIntersecting) {
      position = Position.INSIDE;
    } else if (coord > rootEnd) {
      position = Position.AFTER;
    } else if (coord < rootStart) {
      position = Position.BEFORE;
    }
    const previousPosition = prevPositionRef.current;
    if (previousPosition === position) {
      return;
    }
    handler({
      position,
      previousPosition
    }, entry, observer);
    prevPositionRef.current = position;
  }, {
    threshold,
    root: realRoot,
    rootMargin: toCss(rootMargin)
  });
}
var _default = exports.default = useWaypoint;