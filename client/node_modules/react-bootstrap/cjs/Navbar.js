"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _SelectableContext = _interopRequireDefault(require("@restart/ui/SelectableContext"));
var _uncontrollable = require("uncontrollable");
var _NavbarBrand = _interopRequireDefault(require("./NavbarBrand"));
var _NavbarCollapse = _interopRequireDefault(require("./NavbarCollapse"));
var _NavbarToggle = _interopRequireDefault(require("./NavbarToggle"));
var _NavbarOffcanvas = _interopRequireDefault(require("./NavbarOffcanvas"));
var _ThemeProvider = require("./ThemeProvider");
var _NavbarContext = _interopRequireDefault(require("./NavbarContext"));
var _NavbarText = _interopRequireDefault(require("./NavbarText"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const Navbar = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    bsPrefix: initialBsPrefix,
    expand = true,
    variant = 'light',
    bg,
    fixed,
    sticky,
    className,
    // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
    as: Component = 'nav',
    expanded,
    onToggle,
    onSelect,
    collapseOnSelect = false,
    ...controlledProps
  } = (0, _uncontrollable.useUncontrolled)(props, {
    expanded: 'onToggle'
  });
  const bsPrefix = (0, _ThemeProvider.useBootstrapPrefix)(initialBsPrefix, 'navbar');
  const handleCollapse = (0, _react.useCallback)((...args) => {
    onSelect == null || onSelect(...args);
    if (collapseOnSelect && expanded) {
      onToggle == null || onToggle(false);
    }
  }, [onSelect, collapseOnSelect, expanded, onToggle]);

  // will result in some false positives but that seems better
  // than false negatives. strict `undefined` check allows explicit
  // "nulling" of the role if the user really doesn't want one
  if (controlledProps.role === undefined && Component !== 'nav') {
    controlledProps.role = 'navigation';
  }
  let expandClass = `${bsPrefix}-expand`;
  if (typeof expand === 'string') expandClass = `${expandClass}-${expand}`;
  const navbarContext = (0, _react.useMemo)(() => ({
    onToggle: () => onToggle == null ? void 0 : onToggle(!expanded),
    bsPrefix,
    expanded: !!expanded,
    expand
  }), [bsPrefix, expanded, expand, onToggle]);
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_NavbarContext.default.Provider, {
    value: navbarContext,
    children: /*#__PURE__*/(0, _jsxRuntime.jsx)(_SelectableContext.default.Provider, {
      value: handleCollapse,
      children: /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, {
        ref: ref,
        ...controlledProps,
        className: (0, _classnames.default)(className, bsPrefix, expand && expandClass, variant && `${bsPrefix}-${variant}`, bg && `bg-${bg}`, sticky && `sticky-${sticky}`, fixed && `fixed-${fixed}`)
      })
    })
  });
});
Navbar.displayName = 'Navbar';
var _default = exports.default = Object.assign(Navbar, {
  Brand: _NavbarBrand.default,
  Collapse: _NavbarCollapse.default,
  Offcanvas: _NavbarOffcanvas.default,
  Text: _NavbarText.default,
  Toggle: _NavbarToggle.default
});
module.exports = exports.default;