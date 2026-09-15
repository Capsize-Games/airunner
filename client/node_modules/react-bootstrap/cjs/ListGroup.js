"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var React = _interopRequireWildcard(require("react"));
var _warning = _interopRequireDefault(require("warning"));
var _uncontrollable = require("uncontrollable");
var _Nav = _interopRequireDefault(require("@restart/ui/Nav"));
var _ThemeProvider = require("./ThemeProvider");
var _ListGroupItem = _interopRequireDefault(require("./ListGroupItem"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const ListGroup = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    className,
    bsPrefix: initialBsPrefix,
    variant,
    horizontal,
    numbered,
    // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
    as = 'div',
    ...controlledProps
  } = (0, _uncontrollable.useUncontrolled)(props, {
    activeKey: 'onSelect'
  });
  const bsPrefix = (0, _ThemeProvider.useBootstrapPrefix)(initialBsPrefix, 'list-group');
  let horizontalVariant;
  if (horizontal) {
    horizontalVariant = horizontal === true ? 'horizontal' : `horizontal-${horizontal}`;
  }
  process.env.NODE_ENV !== "production" ? (0, _warning.default)(!(horizontal && variant === 'flush'), '`variant="flush"` and `horizontal` should not be used together.') : void 0;
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_Nav.default, {
    ref: ref,
    ...controlledProps,
    as: as,
    className: (0, _classnames.default)(className, bsPrefix, variant && `${bsPrefix}-${variant}`, horizontalVariant && `${bsPrefix}-${horizontalVariant}`, numbered && `${bsPrefix}-numbered`)
  });
});
ListGroup.displayName = 'ListGroup';
var _default = exports.default = Object.assign(ListGroup, {
  Item: _ListGroupItem.default
});
module.exports = exports.default;