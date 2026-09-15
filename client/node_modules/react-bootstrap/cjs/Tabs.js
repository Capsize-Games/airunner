"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _uncontrollable = require("uncontrollable");
var _Tabs = _interopRequireDefault(require("@restart/ui/Tabs"));
var _Nav = _interopRequireDefault(require("./Nav"));
var _NavLink = _interopRequireDefault(require("./NavLink"));
var _NavItem = _interopRequireDefault(require("./NavItem"));
var _TabContent = _interopRequireDefault(require("./TabContent"));
var _TabPane = _interopRequireDefault(require("./TabPane"));
var _ElementChildren = require("./ElementChildren");
var _getTabTransitionComponent = _interopRequireDefault(require("./getTabTransitionComponent"));
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function getDefaultActiveKey(children) {
  let defaultActiveKey;
  (0, _ElementChildren.forEach)(children, child => {
    if (defaultActiveKey == null) {
      defaultActiveKey = child.props.eventKey;
    }
  });
  return defaultActiveKey;
}
function renderTab(child) {
  const {
    title,
    eventKey,
    disabled,
    tabClassName,
    tabAttrs,
    id
  } = child.props;
  if (title == null) {
    return null;
  }
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_NavItem.default, {
    as: "li",
    role: "presentation",
    children: /*#__PURE__*/(0, _jsxRuntime.jsx)(_NavLink.default, {
      as: "button",
      type: "button",
      eventKey: eventKey,
      disabled: disabled,
      id: id,
      className: tabClassName,
      ...tabAttrs,
      children: title
    })
  });
}
const Tabs = props => {
  const {
    id,
    onSelect,
    transition,
    mountOnEnter = false,
    unmountOnExit = false,
    variant = 'tabs',
    children,
    activeKey = getDefaultActiveKey(children),
    ...controlledProps
  } = (0, _uncontrollable.useUncontrolled)(props, {
    activeKey: 'onSelect'
  });
  return /*#__PURE__*/(0, _jsxRuntime.jsxs)(_Tabs.default, {
    id: id,
    activeKey: activeKey,
    onSelect: onSelect,
    transition: (0, _getTabTransitionComponent.default)(transition),
    mountOnEnter: mountOnEnter,
    unmountOnExit: unmountOnExit,
    children: [/*#__PURE__*/(0, _jsxRuntime.jsx)(_Nav.default, {
      id: id,
      ...controlledProps,
      role: "tablist",
      as: "ul",
      variant: variant,
      children: (0, _ElementChildren.map)(children, renderTab)
    }), /*#__PURE__*/(0, _jsxRuntime.jsx)(_TabContent.default, {
      children: (0, _ElementChildren.map)(children, child => {
        const childProps = {
          ...child.props
        };
        delete childProps.title;
        delete childProps.disabled;
        delete childProps.tabClassName;
        delete childProps.tabAttrs;
        return /*#__PURE__*/(0, _jsxRuntime.jsx)(_TabPane.default, {
          ...childProps
        });
      })
    })]
  });
};
Tabs.displayName = 'Tabs';
var _default = exports.default = Tabs;
module.exports = exports.default;