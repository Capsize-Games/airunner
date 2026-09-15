"use strict";

exports.__esModule = true;
exports.default = useScrollParent;
var _useIsomorphicEffect = _interopRequireDefault(require("@restart/hooks/useIsomorphicEffect"));
var _scrollParent = _interopRequireDefault(require("dom-helpers/scrollParent"));
var _react = require("react");
function _interopRequireDefault(e) { return e && e.__esModule ? e : { default: e }; }
function useScrollParent(element) {
  const [parent, setParent] = (0, _react.useState)(null);
  (0, _useIsomorphicEffect.default)(() => {
    if (element) {
      setParent((0, _scrollParent.default)(element, true));
    }
  }, [element]);
  return parent;
}