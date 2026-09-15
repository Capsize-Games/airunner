"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _propTypes = _interopRequireDefault(require("prop-types"));
var _Button = _interopRequireDefault(require("./Button"));
var _ButtonGroup = _interopRequireDefault(require("./ButtonGroup"));
var _Dropdown = _interopRequireDefault(require("./Dropdown"));
var _types = require("./types");
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const propTypes = {
  /**
   * An html id attribute for the Toggle button, necessary for assistive technologies, such as screen readers.
   * @type {string}
   * @required
   */
  id: _propTypes.default.string,
  /**
   * Accessible label for the toggle; the value of `title` if not specified.
   */
  toggleLabel: _propTypes.default.string,
  /** An `href` passed to the non-toggle Button */
  href: _propTypes.default.string,
  /** An anchor `target` passed to the non-toggle Button */
  target: _propTypes.default.string,
  /** An `onClick` handler passed to the non-toggle Button */
  onClick: _propTypes.default.func,
  /** The content of the non-toggle Button.  */
  title: _propTypes.default.node.isRequired,
  /** A `type` passed to the non-toggle Button */
  type: _propTypes.default.string,
  /** Disables both Buttons  */
  disabled: _propTypes.default.bool,
  /**
   * Aligns the dropdown menu.
   *
   * _see [DropdownMenu](#dropdown-menu-props) for more details_
   *
   * @type {"start"|"end"|{ sm: "start"|"end" }|{ md: "start"|"end" }|{ lg: "start"|"end" }|{ xl: "start"|"end"}|{ xxl: "start"|"end"} }
   */
  align: _types.alignPropType,
  /** An ARIA accessible role applied to the Menu component. When set to 'menu', The dropdown */
  menuRole: _propTypes.default.string,
  /** Whether to render the dropdown menu in the DOM before the first time it is shown */
  renderMenuOnMount: _propTypes.default.bool,
  /**
   *  Which event when fired outside the component will cause it to be closed.
   *
   * _see [DropdownMenu](#dropdown-menu-props) for more details_
   */
  rootCloseEvent: _propTypes.default.string,
  /**
   * Allow Dropdown to flip in case of an overlapping on the reference element. For more information refer to
   * Popper.js's flip [docs](https://popper.js.org/docs/v2/modifiers/flip/).
   *
   */
  flip: _propTypes.default.bool,
  /** @ignore */
  bsPrefix: _propTypes.default.string,
  /** @ignore */
  variant: _propTypes.default.string,
  /** @ignore */
  size: _propTypes.default.string
};

/**
 * A convenience component for simple or general use split button dropdowns. Renders a
 * `ButtonGroup` containing a `Button` and a `Button` toggle for the `Dropdown`. All `children`
 * are passed directly to the default `Dropdown.Menu`. This component accepts all of [`Dropdown`'s
 * props](#dropdown-props).
 *
 * _All unknown props are passed through to the `Dropdown` component._
 * The Button `variant`, `size` and `bsPrefix` props are passed to the button and toggle,
 * and menu-related props are passed to the `Dropdown.Menu`
 */
const SplitButton = /*#__PURE__*/React.forwardRef(({
  id,
  bsPrefix,
  size,
  variant,
  title,
  type = 'button',
  toggleLabel = 'Toggle dropdown',
  children,
  onClick,
  href,
  target,
  menuRole,
  renderMenuOnMount,
  rootCloseEvent,
  flip,
  ...props
}, ref) => /*#__PURE__*/(0, _jsxRuntime.jsxs)(_Dropdown.default, {
  ref: ref,
  ...props,
  as: _ButtonGroup.default,
  children: [/*#__PURE__*/(0, _jsxRuntime.jsx)(_Button.default, {
    size: size,
    variant: variant,
    disabled: props.disabled,
    bsPrefix: bsPrefix,
    href: href,
    target: target,
    onClick: onClick,
    type: type,
    children: title
  }), /*#__PURE__*/(0, _jsxRuntime.jsx)(_Dropdown.default.Toggle, {
    split: true,
    id: id,
    size: size,
    variant: variant,
    disabled: props.disabled,
    childBsPrefix: bsPrefix,
    children: /*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
      className: "visually-hidden",
      children: toggleLabel
    })
  }), /*#__PURE__*/(0, _jsxRuntime.jsx)(_Dropdown.default.Menu, {
    role: menuRole,
    renderOnMount: renderMenuOnMount,
    rootCloseEvent: rootCloseEvent,
    flip: flip,
    children: children
  })]
}));
SplitButton.propTypes = propTypes;
SplitButton.displayName = 'SplitButton';
var _default = exports.default = SplitButton;
module.exports = exports.default;