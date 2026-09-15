"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _Tabs = _interopRequireDefault(require("@restart/ui/Tabs"));
var _getTabTransitionComponent = _interopRequireDefault(require("./getTabTransitionComponent"));
var _jsxRuntime = require("react/jsx-runtime");
const TabContainer = ({
  transition,
  ...props
}) => /*#__PURE__*/(0, _jsxRuntime.jsx)(_Tabs.default, {
  ...props,
  transition: (0, _getTabTransitionComponent.default)(transition)
});
TabContainer.displayName = 'TabContainer';
var _default = exports.default = TabContainer;
module.exports = exports.default;