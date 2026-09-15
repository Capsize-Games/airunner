"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _invariant = _interopRequireDefault(require("invariant"));
var _uncontrollable = require("uncontrollable");
var _createChainedFunction = _interopRequireDefault(require("./createChainedFunction"));
var _ElementChildren = require("./ElementChildren");
var _ButtonGroup = _interopRequireDefault(require("./ButtonGroup"));
var _ToggleButton = _interopRequireDefault(require("./ToggleButton"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const ToggleButtonGroup = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    children,
    type = 'radio',
    name,
    value,
    onChange,
    vertical = false,
    ...controlledProps
  } = (0, _uncontrollable.useUncontrolled)(props, {
    value: 'onChange'
  });
  const getValues = () => value == null ? [] : [].concat(value);
  const handleToggle = (inputVal, event) => {
    if (!onChange) {
      return;
    }
    const values = getValues();
    const isActive = values.indexOf(inputVal) !== -1;
    if (type === 'radio') {
      if (!isActive) onChange(inputVal, event);
      return;
    }
    if (isActive) {
      onChange(values.filter(n => n !== inputVal), event);
    } else {
      onChange([...values, inputVal], event);
    }
  };
  !(type !== 'radio' || !!name) ? process.env.NODE_ENV !== "production" ? (0, _invariant.default)(false, 'A `name` is required to group the toggle buttons when the `type` ' + 'is set to "radio"') : (0, _invariant.default)(false) : void 0;
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_ButtonGroup.default, {
    ...controlledProps,
    ref: ref,
    vertical: vertical,
    children: (0, _ElementChildren.map)(children, child => {
      const values = getValues();
      const {
        value: childVal,
        onChange: childOnChange
      } = child.props;
      const handler = e => handleToggle(childVal, e);
      return /*#__PURE__*/React.cloneElement(child, {
        type,
        name: child.name || name,
        checked: values.indexOf(childVal) !== -1,
        onChange: (0, _createChainedFunction.default)(childOnChange, handler)
      });
    })
  });
});
ToggleButtonGroup.displayName = 'ToggleButtonGroup';
var _default = exports.default = Object.assign(ToggleButtonGroup, {
  Button: _ToggleButton.default
});
module.exports = exports.default;