"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var _propTypes = _interopRequireDefault(require("prop-types"));
var React = _interopRequireWildcard(require("react"));
var _FormCheck = _interopRequireDefault(require("./FormCheck"));
var _FormControl = _interopRequireDefault(require("./FormControl"));
var _FormFloating = _interopRequireDefault(require("./FormFloating"));
var _FormGroup = _interopRequireDefault(require("./FormGroup"));
var _FormLabel = _interopRequireDefault(require("./FormLabel"));
var _FormRange = _interopRequireDefault(require("./FormRange"));
var _FormSelect = _interopRequireDefault(require("./FormSelect"));
var _FormText = _interopRequireDefault(require("./FormText"));
var _Switch = _interopRequireDefault(require("./Switch"));
var _FloatingLabel = _interopRequireDefault(require("./FloatingLabel"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const propTypes = {
  /**
   * The Form `ref` will be forwarded to the underlying element,
   * which means, unless it's rendered `as` a composite component,
   * it will be a DOM node, when resolved.
   *
   * @type {ReactRef}
   * @alias ref
   */
  _ref: _propTypes.default.any,
  /**
   * Mark a form as having been validated. Setting it to `true` will
   * toggle any validation styles on the forms elements.
   */
  validated: _propTypes.default.bool,
  as: _propTypes.default.elementType
};
const Form = /*#__PURE__*/React.forwardRef(({
  className,
  validated,
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'form',
  ...props
}, ref) => /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, {
  ...props,
  ref: ref,
  className: (0, _classnames.default)(className, validated && 'was-validated')
}));
Form.displayName = 'Form';
Form.propTypes = propTypes;
var _default = exports.default = Object.assign(Form, {
  Group: _FormGroup.default,
  Control: _FormControl.default,
  Floating: _FormFloating.default,
  Check: _FormCheck.default,
  Switch: _Switch.default,
  Label: _FormLabel.default,
  Text: _FormText.default,
  Range: _FormRange.default,
  Select: _FormSelect.default,
  FloatingLabel: _FloatingLabel.default
});
module.exports = exports.default;