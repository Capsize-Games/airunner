"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var React = _interopRequireWildcard(require("react"));
var _ThemeProvider = require("./ThemeProvider");
var _Dropdown = _interopRequireDefault(require("./Dropdown"));
var _NavLink = _interopRequireDefault(require("./NavLink"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const NavDropdown = /*#__PURE__*/React.forwardRef(({
  id,
  title,
  children,
  bsPrefix,
  className,
  rootCloseEvent,
  menuRole,
  disabled,
  active,
  renderMenuOnMount,
  menuVariant,
  ...props
}, ref) => {
  /* NavItem has no additional logic, it's purely presentational. Can set nav item class here to support "as" */
  const navItemPrefix = (0, _ThemeProvider.useBootstrapPrefix)(undefined, 'nav-item');
  return /*#__PURE__*/(0, _jsxRuntime.jsxs)(_Dropdown.default, {
    ref: ref,
    ...props,
    className: (0, _classnames.default)(className, navItemPrefix),
    children: [/*#__PURE__*/(0, _jsxRuntime.jsx)(_Dropdown.default.Toggle, {
      id: id,
      eventKey: null,
      active: active,
      disabled: disabled,
      childBsPrefix: bsPrefix,
      as: _NavLink.default,
      children: title
    }), /*#__PURE__*/(0, _jsxRuntime.jsx)(_Dropdown.default.Menu, {
      role: menuRole,
      renderOnMount: renderMenuOnMount,
      rootCloseEvent: rootCloseEvent,
      variant: menuVariant,
      children: children
    })]
  });
});
NavDropdown.displayName = 'NavDropdown';
var _default = exports.default = Object.assign(NavDropdown, {
  Item: _Dropdown.default.Item,
  ItemText: _Dropdown.default.ItemText,
  Divider: _Dropdown.default.Divider,
  Header: _Dropdown.default.Header
});
module.exports = exports.default;