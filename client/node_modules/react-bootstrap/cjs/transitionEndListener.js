"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = transitionEndListener;
var _css = _interopRequireDefault(require("dom-helpers/css"));
var _transitionEnd = _interopRequireDefault(require("dom-helpers/transitionEnd"));
function parseDuration(node, property) {
  const str = (0, _css.default)(node, property) || '';
  const mult = str.indexOf('ms') === -1 ? 1000 : 1;
  return parseFloat(str) * mult;
}
function transitionEndListener(element, handler) {
  const duration = parseDuration(element, 'transitionDuration');
  const delay = parseDuration(element, 'transitionDelay');
  const remove = (0, _transitionEnd.default)(element, e => {
    if (e.target === element) {
      remove();
      handler(e);
    }
  }, duration + delay);
}
module.exports = exports.default;