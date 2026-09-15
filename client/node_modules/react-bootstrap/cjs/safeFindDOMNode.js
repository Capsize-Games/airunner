"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = safeFindDOMNode;
var _reactDom = _interopRequireDefault(require("react-dom"));
function safeFindDOMNode(componentOrElement) {
  if (componentOrElement && 'setState' in componentOrElement) {
    // TODO: Remove in next major.
    // eslint-disable-next-line react/no-find-dom-node
    return _reactDom.default.findDOMNode(componentOrElement);
  }
  return componentOrElement != null ? componentOrElement : null;
}
module.exports = exports.default;