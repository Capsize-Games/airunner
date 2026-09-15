"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.alignPropType = void 0;
var _propTypes = _interopRequireDefault(require("prop-types"));
const alignDirection = _propTypes.default.oneOf(['start', 'end']);
const alignPropType = exports.alignPropType = _propTypes.default.oneOfType([alignDirection, _propTypes.default.shape({
  sm: alignDirection
}), _propTypes.default.shape({
  md: alignDirection
}), _propTypes.default.shape({
  lg: alignDirection
}), _propTypes.default.shape({
  xl: alignDirection
}), _propTypes.default.shape({
  xxl: alignDirection
}), _propTypes.default.object]);