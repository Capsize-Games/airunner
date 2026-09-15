"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _Feedback = _interopRequireDefault(require("./Feedback"));
var _FormCheckInput = _interopRequireDefault(require("./FormCheckInput"));
var _FormCheckLabel = _interopRequireDefault(require("./FormCheckLabel"));
var _FormContext = _interopRequireDefault(require("./FormContext"));
var _ThemeProvider = require("./ThemeProvider");
var _ElementChildren = require("./ElementChildren");
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const FormCheck = /*#__PURE__*/React.forwardRef(({
  id,
  bsPrefix,
  bsSwitchPrefix,
  inline = false,
  reverse = false,
  disabled = false,
  isValid = false,
  isInvalid = false,
  feedbackTooltip = false,
  feedback,
  feedbackType,
  className,
  style,
  title = '',
  type = 'checkbox',
  label,
  children,
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as = 'input',
  ...props
}, ref) => {
  bsPrefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'form-check');
  bsSwitchPrefix = (0, _ThemeProvider.useBootstrapPrefix)(bsSwitchPrefix, 'form-switch');
  const {
    controlId
  } = (0, _react.useContext)(_FormContext.default);
  const innerFormContext = (0, _react.useMemo)(() => ({
    controlId: id || controlId
  }), [controlId, id]);
  const hasLabel = !children && label != null && label !== false || (0, _ElementChildren.hasChildOfType)(children, _FormCheckLabel.default);
  const input = /*#__PURE__*/(0, _jsxRuntime.jsx)(_FormCheckInput.default, {
    ...props,
    type: type === 'switch' ? 'checkbox' : type,
    ref: ref,
    isValid: isValid,
    isInvalid: isInvalid,
    disabled: disabled,
    as: as
  });
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_FormContext.default.Provider, {
    value: innerFormContext,
    children: /*#__PURE__*/(0, _jsxRuntime.jsx)("div", {
      style: style,
      className: (0, _classnames.default)(className, hasLabel && bsPrefix, inline && `${bsPrefix}-inline`, reverse && `${bsPrefix}-reverse`, type === 'switch' && bsSwitchPrefix),
      children: children || /*#__PURE__*/(0, _jsxRuntime.jsxs)(_jsxRuntime.Fragment, {
        children: [input, hasLabel && /*#__PURE__*/(0, _jsxRuntime.jsx)(_FormCheckLabel.default, {
          title: title,
          children: label
        }), feedback && /*#__PURE__*/(0, _jsxRuntime.jsx)(_Feedback.default, {
          type: feedbackType,
          tooltip: feedbackTooltip,
          children: feedback
        })]
      })
    })
  });
});
FormCheck.displayName = 'FormCheck';
var _default = exports.default = Object.assign(FormCheck, {
  Input: _FormCheckInput.default,
  Label: _FormCheckLabel.default
});
module.exports = exports.default;