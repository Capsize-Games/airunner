"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var React = _interopRequireWildcard(require("react"));
var _ThemeProvider = require("./ThemeProvider");
var _BreadcrumbItem = _interopRequireDefault(require("./BreadcrumbItem"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const Breadcrumb = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  listProps = {},
  children,
  label = 'breadcrumb',
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'nav',
  ...props
}, ref) => {
  const prefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'breadcrumb');
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, {
    "aria-label": label,
    className: className,
    ref: ref,
    ...props,
    children: /*#__PURE__*/(0, _jsxRuntime.jsx)("ol", {
      ...listProps,
      className: (0, _classnames.default)(prefix, listProps == null ? void 0 : listProps.className),
      children: children
    })
  });
});
Breadcrumb.displayName = 'Breadcrumb';
var _default = exports.default = Object.assign(Breadcrumb, {
  Item: _BreadcrumbItem.default
});
module.exports = exports.default;