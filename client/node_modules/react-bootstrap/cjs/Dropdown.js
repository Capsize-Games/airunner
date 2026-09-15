"use strict";
"use client";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _classnames = _interopRequireDefault(require("classnames"));
var _react = _interopRequireWildcard(require("react"));
var React = _react;
var _Dropdown = _interopRequireDefault(require("@restart/ui/Dropdown"));
var _uncontrollable = require("uncontrollable");
var _useEventCallback = _interopRequireDefault(require("@restart/hooks/useEventCallback"));
var _DropdownContext = _interopRequireDefault(require("./DropdownContext"));
var _DropdownDivider = _interopRequireDefault(require("./DropdownDivider"));
var _DropdownHeader = _interopRequireDefault(require("./DropdownHeader"));
var _DropdownItem = _interopRequireDefault(require("./DropdownItem"));
var _DropdownItemText = _interopRequireDefault(require("./DropdownItemText"));
var _DropdownMenu = _interopRequireWildcard(require("./DropdownMenu"));
var _DropdownToggle = _interopRequireDefault(require("./DropdownToggle"));
var _InputGroupContext = _interopRequireDefault(require("./InputGroupContext"));
var _ThemeProvider = require("./ThemeProvider");
var _types = require("./types");
var _jsxRuntime = require("react/jsx-runtime");
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
const Dropdown = /*#__PURE__*/React.forwardRef((pProps, ref) => {
  const {
    bsPrefix,
    drop = 'down',
    show,
    className,
    align = 'start',
    onSelect,
    onToggle,
    focusFirstItemOnShow,
    // Need to define the default "as" during prop destructuring to be compatible with styled-components github.com/react-bootstrap/react-bootstrap/issues/3595
    as: Component = 'div',
    navbar: _4,
    autoClose = true,
    ...props
  } = (0, _uncontrollable.useUncontrolled)(pProps, {
    show: 'onToggle'
  });
  const isInputGroup = (0, _react.useContext)(_InputGroupContext.default);
  const prefix = (0, _ThemeProvider.useBootstrapPrefix)(bsPrefix, 'dropdown');
  const isRTL = (0, _ThemeProvider.useIsRTL)();
  const isClosingPermitted = source => {
    // autoClose=false only permits close on button click
    if (autoClose === false) return source === 'click';

    // autoClose=inside doesn't permit close on rootClose
    if (autoClose === 'inside') return source !== 'rootClose';

    // autoClose=outside doesn't permit close on select
    if (autoClose === 'outside') return source !== 'select';
    return true;
  };
  const handleToggle = (0, _useEventCallback.default)((nextShow, meta) => {
    var _meta$originalEvent;
    /** Checking if target of event is ToggleButton,
     * if it is then nullify mousedown event
     */
    const isToggleButton = (_meta$originalEvent = meta.originalEvent) == null || (_meta$originalEvent = _meta$originalEvent.target) == null ? void 0 : _meta$originalEvent.classList.contains('dropdown-toggle');
    if (isToggleButton && meta.source === 'mousedown') {
      return;
    }
    if (meta.originalEvent.currentTarget === document && (meta.source !== 'keydown' || meta.originalEvent.key === 'Escape')) meta.source = 'rootClose';
    if (isClosingPermitted(meta.source)) onToggle == null || onToggle(nextShow, meta);
  });
  const alignEnd = align === 'end';
  const placement = (0, _DropdownMenu.getDropdownMenuPlacement)(alignEnd, drop, isRTL);
  const contextValue = (0, _react.useMemo)(() => ({
    align,
    drop,
    isRTL
  }), [align, drop, isRTL]);
  const directionClasses = {
    down: prefix,
    'down-centered': `${prefix}-center`,
    up: 'dropup',
    'up-centered': 'dropup-center dropup',
    end: 'dropend',
    start: 'dropstart'
  };
  return /*#__PURE__*/(0, _jsxRuntime.jsx)(_DropdownContext.default.Provider, {
    value: contextValue,
    children: /*#__PURE__*/(0, _jsxRuntime.jsx)(_Dropdown.default, {
      placement: placement,
      show: show,
      onSelect: onSelect,
      onToggle: handleToggle,
      focusFirstItemOnShow: focusFirstItemOnShow,
      itemSelector: `.${prefix}-item:not(.disabled):not(:disabled)`,
      children: isInputGroup ? props.children : /*#__PURE__*/(0, _jsxRuntime.jsx)(Component, {
        ...props,
        ref: ref,
        className: (0, _classnames.default)(className, show && 'show', directionClasses[drop])
      })
    })
  });
});
Dropdown.displayName = 'Dropdown';
var _default = exports.default = Object.assign(Dropdown, {
  Toggle: _DropdownToggle.default,
  Menu: _DropdownMenu.default,
  Item: _DropdownItem.default,
  ItemText: _DropdownItemText.default,
  Divider: _DropdownDivider.default,
  Header: _DropdownHeader.default
});
module.exports = exports.default;