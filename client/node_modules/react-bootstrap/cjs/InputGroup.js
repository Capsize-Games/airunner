"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _ThemeProvider = require("./ThemeProvider");
var _FormCheckInput = _interopRequireDefault(require("./FormCheckInput"));
var _InputGroupContext = _interopRequireDefault(require("./InputGroupContext"));
var _InputGroupText = _interopRequireDefault(require("./InputGroupText"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const InputGroupCheckbox = props => /*#__PURE__*/(0, _jsxRuntime.jsx)(_InputGroupText.default, {
  children: /*#__PURE__*/(0, _jsxRuntime.jsx)(_FormCheckInput.default, {
    type: "checkbox",
    ...props
  })
});
const InputGroupRadio = props => /*#__PURE__*/(0, _jsxRuntime.jsx)(_InputGroupText.default, {
  children: /*#__PURE__*/(0, _jsxRuntime.jsx)(_FormCheckInput.default, {
    type: "radio",
    ...props
  })
});
const InputGroup = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  size,
  hasValidation,
  className,
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'div',
  ...props
}, ref) => {
  bsPrefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'input-group');

  // Intentionally an empty object. Used in detecting if a dropdown
  // exists under an input group.
  const contextValue = (0, _react.useMemo)(() => ({}), []);
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_InputGroupContext.default.Provider, {
    value: contextValue,
    children: /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, {
      ref: ref,
      ...props,
      className: (0, _classnames.default)(className, bsPrefix, size && `${bsPrefix}-${size}`, hasValidation && 'has-validation')
    })
  });
});
InputGroup.displayName = 'InputGroup';
var _default = exports.default = Object.assign(InputGroup, {
  Text: _InputGroupText.default,
  Radio: InputGroupRadio,
  Checkbox: InputGroupCheckbox
});
module.exports = exports.default;