"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = getTabTransitionComponent;
var _NoopTransition = _interopRequireDefault(require("@restart/ui/NoopTransition"));
var _Fade = _interopRequireDefault(require("./Fade"));
function getTabTransitionComponent(transition) {
  if (typeof transition === 'boolean') {
    return transition ? _Fade.default : _NoopTransition.default;
  }
  return transition;
}
module.exports = exports.default;