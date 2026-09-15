"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = usePlaceholder;
var _classnames = _interopRequireDefault(require("classnames"));
var _ThemeProvider = require("./ThemeProvider");
var _Col = require("./Col");
function usePlaceholder({
  animation,
  bg,
  bsPrefix,
  size,
  ...props
}) {
  bsPrefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'placeholder');
  const [{
    className,
    ...colProps
  }] = (0, _Col.useCol)(props);
  return {
    ...colProps,
    className: (0, _classnames.default)(className, animation ? `${bsPrefix}-${animation}` : bsPrefix, size && `${bsPrefix}-${size}`, bg && `bg-${bg}`)
  };
}
module.exports = exports.default;