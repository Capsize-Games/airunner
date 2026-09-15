"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = useOverlayOffset;
var _react = require("react");
var _hasClass = _interopRequireDefault(require("dom-helpers/hasClass"));
var _ThemeProvider = require("./ThemeProvider");
var _Popover = _interopRequireDefault(require("./Popover"));
var _Tooltip = _interopRequireDefault(require("./Tooltip"));
// This is meant for internal use.
// This applies a custom offset to the overlay if it's a popover or tooltip.
function useOverlayOffset(customOffset) {
  const overlayRef = (0, _react.useRef)(null);
  const popoverClass = (0, _ThemeProvider.useBootstrapPrefix)(undefined, 'popover');
  const tooltipClass = (0, _ThemeProvider.useBootstrapPrefix)(undefined, 'tooltip');
  const offset = (0, _react.useMemo)(() => ({
    name: 'offset',
    options: {
      offset: () => {
        if (customOffset) {
          return customOffset;
        }
        if (overlayRef.current) {
          if ((0, _hasClass.default)(overlayRef.current, popoverClass)) {
            return _Popover.default.POPPER_OFFSET;
          }
          if ((0, _hasClass.default)(overlayRef.current, tooltipClass)) {
            return _Tooltip.default.TOOLTIP_OFFSET;
          }
        }
        return [0, 0];
      }
    }
  }), [customOffset, popoverClass, tooltipClass]);
  return [overlayRef, [offset]];
}
module.exports = exports.default;