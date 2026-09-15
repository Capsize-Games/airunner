import classNames from 'classnames';
import * as React from 'react';
import Anchor from '@restart/ui/Anchor';
import { jsx as _jsx } from "react/jsx-runtime";
import { jsxs as _jsxs } from "react/jsx-runtime";
const PageItem = /*#__PURE__*/React.forwardRef(({
  active = false,
  disabled = false,
  className,
  style,
  activeLabel = '(current)',
  children,
  linkStyle,
  linkClassName,
  as = Anchor,
  ...props
}, ref) => {
  const Component = active || disabled ? 'span' : as;
  return /*#__PURE__*/_jsx("li", {
    ref: ref,
    style: style,
    className: classNames(className, 'page-item', {
      active,
      disabled
    }),
    children: /*#__PURE__*/_jsxs(Component, {
      className: classNames('page-link', linkClassName),
      style: linkStyle,
      ...props,
      children: [children, active && activeLabel && /*#__PURE__*/_jsx("span", {
        className: "visually-hidden",
        children: activeLabel
      })]
    })
  });
});
PageItem.displayName = 'PageItem';
export default PageItem;
function createButton(name, defaultValue, label = name) {
  const Button = /*#__PURE__*/React.forwardRef(({
    children,
    ...props
  }, ref) => /*#__PURE__*/_jsxs(PageItem, {
    ...props,
    ref: ref,
    children: [/*#__PURE__*/_jsx("span", {
      "aria-hidden": "true",
      children: children || defaultValue
    }), /*#__PURE__*/_jsx("span", {
      className: "visually-hidden",
      children: label
    })]
  }));
  Button.displayName = name;
  return Button;
}
export const First = createButton('First', '«');
export const Prev = createButton('Prev', '‹', 'Previous');
export const Ellipsis = createButton('Ellipsis', '…', 'More');
export const Next = createButton('Next', '›');
export const Last = createButton('Last', '»');