"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var React = _interopRequireWildcard(require("react"));
var _ThemeProvider = require("./ThemeProvider");
var _CardBody = _interopRequireDefault(require("./CardBody"));
var _CardFooter = _interopRequireDefault(require("./CardFooter"));
var _CardHeader = _interopRequireDefault(require("./CardHeader"));
var _CardImg = _interopRequireDefault(require("./CardImg"));
var _CardImgOverlay = _interopRequireDefault(require("./CardImgOverlay"));
var _CardLink = _interopRequireDefault(require("./CardLink"));
var _CardSubtitle = _interopRequireDefault(require("./CardSubtitle"));
var _CardText = _interopRequireDefault(require("./CardText"));
var _CardTitle = _interopRequireDefault(require("./CardTitle"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const Card = /*#__PURE__*/React.forwardRef(({
  bsPrefix,
  className,
  bg,
  text,
  border,
  body = false,
  children,
  // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
  as: Component = 'div',
  ...props
}, ref) => {
  const prefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'card');
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, {
    ref: ref,
    ...props,
    className: (0, _classnames.default)(className, prefix, bg && `bg-${bg}`, text && `text-${text}`, border && `border-${border}`),
    children: body ? /*#__PURE__*/(0, _jsxRuntime.jsx)(_CardBody.default, {
      children: children
    }) : children
  });
});
Card.displayName = 'Card';
var _default = exports.default = Object.assign(Card, {
  Img: _CardImg.default,
  Title: _CardTitle.default,
  Subtitle: _CardSubtitle.default,
  Body: _CardBody.default,
  Link: _CardLink.default,
  Text: _CardText.default,
  Header: _CardHeader.default,
  Footer: _CardFooter.default,
  ImgOverlay: _CardImgOverlay.default
});
module.exports = exports.default;