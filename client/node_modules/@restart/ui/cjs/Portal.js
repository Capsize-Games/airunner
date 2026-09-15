"use strict";

exports.__esModule = true;
exports.default = void 0;
var _reactDom = _interopRequireDefault(require("react-dom"));
var React = _interopRequireWildcard(require("react"));
var _useWaitForDOMRef = _interopRequireDefault(require("./useWaitForDOMRef"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && {}.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function _interopRequireDefault(e) { return e && e.__esModule ? e : { default: e }; }
/**
 * @public
 */
const Portal = ({
  container,
  children,
  onRendered
}) => {
  const resolvedContainer = (0, _useWaitForDOMRef.default)(container, onRendered);
  return resolvedContainer ? /*#__PURE__*/(0, _jsxRuntime.jsx)(_jsxRuntime.Fragment, {
    children: /*#__PURE__*/_reactDom.default.createPortal(children, resolvedContainer)
  }) : null;
};
Portal.displayName = 'Portal';
var _default = exports.default = Portal;