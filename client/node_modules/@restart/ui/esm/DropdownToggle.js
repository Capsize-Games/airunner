import { useContext, useCallback } from 'react';
import * as React from 'react';
import { useSSRSafeId } from './ssr';
import DropdownContext from './DropdownContext';
import { Fragment as _Fragment, jsx as _jsx } from "react/jsx-runtime";
export const isRoleMenu = el => {
  var _el$getAttribute;
  return ((_el$getAttribute = el.getAttribute('role')) == null ? void 0 : _el$getAttribute.toLowerCase()) === 'menu';
};
const noop = () => {};

/**
 * Wires up Dropdown toggle functionality, returning a set a props to attach
 * to the element that functions as the dropdown toggle (generally a button).
 *
 * @memberOf Dropdown
 */
export function useDropdownToggle() {
  const id = useSSRSafeId();
  const {
    show = false,
    toggle = noop,
    setToggle,
    menuElement
  } = useContext(DropdownContext) || {};
  const handleClick = useCallback(e => {
    toggle(!show, e);
  }, [show, toggle]);
  const props = {
    id,
    ref: setToggle || noop,
    onClick: handleClick,
    'aria-expanded': !!show
  };

  // This is maybe better down in an effect, but
  // the component is going to update anyway when the menu element
  // is set so might return new props.
  if (menuElement && isRoleMenu(menuElement)) {
    props['aria-haspopup'] = true;
  }
  return [props, {
    show,
    toggle
  }];
}
/**
 * Also exported as `<Dropdown.Toggle>` from `Dropdown`.
 *
 * @displayName DropdownToggle
 * @memberOf Dropdown
 */
function DropdownToggle({
  children
}) {
  const [props, meta] = useDropdownToggle();
  return /*#__PURE__*/_jsx(_Fragment, {
    children: children(props, meta)
  });
}
DropdownToggle.displayName = 'DropdownToggle';

/** @component */
export default DropdownToggle;