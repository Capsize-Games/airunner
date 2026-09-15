"use strict";

exports.__esModule = true;
exports.WindowProvider = void 0;
exports.default = useWindow;
var _react = require("react");
var _canUseDOM = _interopRequireDefault(require("dom-helpers/canUseDOM"));
function _interopRequireDefault(e) { return e && e.__esModule ? e : { default: e }; }
const Context = /*#__PURE__*/(0, _react.createContext)(_canUseDOM.default ? window : undefined);
const WindowProvider = exports.WindowProvider = Context.Provider;

/**
 * The document "window" placed in React context. Helpful for determining
 * SSR context, or when rendering into an iframe.
 *
 * @returns the current window
 */
function useWindow() {
  return (0, _react.useContext)(Context);
}