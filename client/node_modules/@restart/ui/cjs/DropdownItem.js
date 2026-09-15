"use strict";

exports.__esModule = true;
exports.default = void 0;
exports.useDropdownItem = useDropdownItem;
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _useEventCallback = _interopRequireDefault(require("@restart/hooks/useEventCallback"));
var _SelectableContext = _interopRequireWildcard(require("./SelectableContext"));
var _NavContext = _interopRequireDefault(require("./NavContext"));
var _Button = _interopRequireDefault(require("./Button"));
var _DataKey = require("./DataKey");
var _jsxRuntime = require("react/jsx-runtime");
const _excluded = ["eventKey", "disabled", "onClick", "active", "as"];
function _interopRequireDefault(e) { return e && e.__esModule ? e : { default: e }; }
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && {}.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function _objectWithoutPropertiesLoose(r, e) { if (null == r) return {}; var t = {}; for (var n in r) if ({}.hasOwnProperty.call(r, n)) { if (e.indexOf(n) >= 0) continue; t[n] = r[n]; } return t; }
/**
 * Create a dropdown item. Returns a set of props for the dropdown item component
 * including an `onClick` handler that prevents selection when the item is disabled
 */
function useDropdownItem({
  key,
  href,
  active,
  disabled,
  onClick
}) {
  const onSelectCtx = (0, _react.useContext)(_SelectableContext.default);
  const navContext = (0, _react.useContext)(_NavContext.default);
  const {
    activeKey
  } = navContext || {};
  const eventKey = (0, _SelectableContext.makeEventKey)(key, href);
  const isActive = active == null && key != null ? (0, _SelectableContext.makeEventKey)(activeKey) === eventKey : active;
  const handleClick = (0, _useEventCallback.default)(event => {
    if (disabled) return;
    onClick == null ? void 0 : onClick(event);
    if (onSelectCtx && !event.isPropagationStopped()) {
      onSelectCtx(eventKey, event);
    }
  });
  return [{
    onClick: handleClick,
    'aria-disabled': disabled || undefined,
    'aria-selected': isActive,
    [(0, _DataKey.dataAttr)('dropdown-item')]: ''
  }, {
    isActive
  }];
}
const DropdownItem = /*#__PURE__*/React.forwardRef((_ref, ref) => {
  let {
      eventKey,
      disabled,
      onClick,
      active,
      as: Component = _Button.default
    } = _ref,
    props = _objectWithoutPropertiesLoose(_ref, _excluded);
  const [dropdownItemProps] = useDropdownItem({
    key: eventKey,
    href: props.href,
    disabled,
    onClick,
    active
  });
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, Object.assign({}, props, {
    ref: ref
  }, dropdownItemProps));
});
DropdownItem.displayName = 'DropdownItem';
var _default = exports.default = DropdownItem;