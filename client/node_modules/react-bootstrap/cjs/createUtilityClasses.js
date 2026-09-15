"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = createUtilityClassName;
exports.responsivePropType = responsivePropType;
var _propTypes = _interopRequireDefault(require("prop-types"));
var _ThemeProvider = require("./ThemeProvider");
function responsivePropType(propType) {
  return _propTypes.default.oneOfType([propType, _propTypes.default.shape({
    xs: propType,
    sm: propType,
    md: propType,
    lg: propType,
    xl: propType,
    xxl: propType
  })]);
}
function createUtilityClassName(utilityValues, breakpoints = _ThemeProvider.DEFAULT_BREAKPOINTS, minBreakpoint = _ThemeProvider.DEFAULT_MIN_BREAKPOINT) {
  const classes = [];
  Object.entries(utilityValues).forEach(([utilName, utilValue]) => {
    if (utilValue != null) {
      if (typeof utilValue === 'object') {
        breakpoints.forEach(brkPoint => {
          const bpValue = utilValue[brkPoint];
          if (bpValue != null) {
            const infix = brkPoint !== minBreakpoint ? `-${brkPoint}` : '';
            classes.push(`${utilName}${infix}-${bpValue}`);
          }
        });
      } else {
        classes.push(`${utilName}-${utilValue}`);
      }
    }
  });
  return classes;
}