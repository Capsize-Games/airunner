import ReactDOM from 'react-dom';
import * as React from 'react';
import useWaitForDOMRef from './useWaitForDOMRef';
import { Fragment as _Fragment, jsx as _jsx } from "react/jsx-runtime";
/**
 * @public
 */
const Portal = ({
  container,
  children,
  onRendered
}) => {
  const resolvedContainer = useWaitForDOMRef(container, onRendered);
  return resolvedContainer ? /*#__PURE__*/_jsx(_Fragment, {
    children: /*#__PURE__*/ReactDOM.createPortal(children, resolvedContainer)
  }) : null;
};
Portal.displayName = 'Portal';
export default Portal;