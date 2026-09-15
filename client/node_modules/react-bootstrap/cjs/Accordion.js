"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _uncontrollable = require("uncontrollable");
var _ThemeProvider = require("./ThemeProvider");
var _AccordionBody = _interopRequireDefault(require("./AccordionBody"));
var _AccordionButton = _interopRequireDefault(require("./AccordionButton"));
var _AccordionCollapse = _interopRequireDefault(require("./AccordionCollapse"));
var _AccordionContext = _interopRequireDefault(require("./AccordionContext"));
var _AccordionHeader = _interopRequireDefault(require("./AccordionHeader"));
var _AccordionItem = _interopRequireDefault(require("./AccordionItem"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const Accordion = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
    as: Component = 'div',
    activeKey,
    bsPrefix,
    className,
    onSelect,
    flush,
    alwaysOpen,
    ...controlledProps
  } = (0, _uncontrollable.useUncontrolled)(props, {
    activeKey: 'onSelect'
  });
  const prefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'accordion');
  const contextValue = (0, _react.useMemo)(() => ({
    activeEventKey: activeKey,
    onSelect,
    alwaysOpen
  }), [activeKey, onSelect, alwaysOpen]);
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_AccordionContext.default.Provider, {
    value: contextValue,
    children: /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, {
      ref: ref,
      ...controlledProps,
      className: (0, _classnames.default)(className, prefix, flush && `${prefix}-flush`)
    })
  });
});
Accordion.displayName = 'Accordion';
var _default = exports.default = Object.assign(Accordion, {
  Button: _AccordionButton.default,
  Collapse: _AccordionCollapse.default,
  Item: _AccordionItem.default,
  Header: _AccordionHeader.default,
  Body: _AccordionBody.default
});
module.exports = exports.default;