"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _useMergedRefs = _interopRequireDefault(require("@restart/hooks/useMergedRefs"));
var _DropdownContext = _interopRequireDefault(require("@restart/ui/DropdownContext"));
var _DropdownToggle = require("@restart/ui/DropdownToggle");
var _classnames = _interopRequireDefault(require("classnames"));
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _Button = _interopRequireDefault(require("./Button"));
var _ThemeProvider = require("./ThemeProvider");
var _useWrappedRefWithWarning = _interopRequireDefault(require("./useWrappedRefWithWarning"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const DropdownToggle = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  split,
  className,
  childBsPrefix,
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = _Button.default,
  ...props
}, ref) => {
  const prefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'dropdown-toggle');
  const dropdownContext = (0, _react.useContext)(_DropdownContext.default);
  if (childBsPrefix !== undefined) {
    props.bsPrefix = childBsPrefix;
  }
  const [toggleProps] = (0, _DropdownToggle.useDropdownToggle)();
  toggleProps.ref = (0, _useMergedRefs.default)(toggleProps.ref, (0, _useWrappedRefWithWarning.default)(ref, 'DropdownToggle'));

  // This intentionally forwards size and variant (if set) to the
  // underlying component, to allow it to render size and style variants.
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, {
    className: (0, _classnames.default)(className, prefix, split && `${prefix}-split`, (dropdownContext == null ? void 0 : dropdownContext.show) && 'show'),
    ...toggleProps,
    ...props
  });
});
DropdownToggle.displayName = 'DropdownToggle';
var _default = exports.default = DropdownToggle;
module.exports = exports.default;