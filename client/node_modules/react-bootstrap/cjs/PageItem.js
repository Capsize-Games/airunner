"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = exports.Prev = exports.Next = exports.Last = exports.First = exports.Ellipsis = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var React = _interopRequireWildcard(require("react"));
var _Anchor = _interopRequireDefault(require("@restart/ui/Anchor"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const PageItem = /*#__PURE__*/React.forwardRef(({
  active = false,
  disabled = false,
  className,
  style,
  activeLabel = '(current)',
  children,
  linkStyle,
  linkClassName,
  as = _Anchor.default,
  ...props
}, ref) => {
  const Component = active || disabled ? 'span' : as;
  return /*#__PURE__*/(0, _jsxRuntime.jsx)("li", {
    ref: ref,
    style: style,
    className: (0, _classnames.default)(className, 'page-item', {
      active,
      disabled
    }),
    children: /*#__PURE__*/(0, _jsxRuntime.jsxs)(Component, {
      className: (0, _classnames.default)('page-link', linkClassName),
      style: linkStyle,
      ...props,
      children: [children, active && activeLabel && /*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
        className: "visually-hidden",
        children: activeLabel
      })]
    })
  });
});
PageItem.displayName = 'PageItem';
var _default = exports.default = PageItem;
function createButton(name, defaultValue, label = name) {
  const Button = /*#__PURE__*/React.forwardRef(({
    children,
    ...props
  }, ref) => /*#__PURE__*/(0, _jsxRuntime.jsxs)(PageItem, {
    ...props,
    ref: ref,
    children: [/*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
      "aria-hidden": "true",
      children: children || defaultValue
    }), /*#__PURE__*/(0, _jsxRuntime.jsx)("span", {
      className: "visually-hidden",
      children: label
    })]
  }));
  Button.displayName = name;
  return Button;
}
const First = exports.First = createButton('First', '«');
const Prev = exports.Prev = createButton('Prev', '‹', 'Previous');
const Ellipsis = exports.Ellipsis = createButton('Ellipsis', '…', 'More');
const Next = exports.Next = createButton('Next', '›');
const Last = exports.Last = createButton('Last', '»');