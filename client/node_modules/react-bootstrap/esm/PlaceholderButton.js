import * as React from 'react';
import Button from './Button';
import usePlaceholder from './usePlaceholder';
import { jsx as _jsx } from "react/jsx-runtime";
const PlaceholderButton = /*#__PURE__*/React.forwardRef((props, ref) => {
  const placeholderProps = usePlaceholder(props);
  return /*#__PURE__*/_jsx(Button, {
    ...placeholderProps,
    ref: ref,
    disabled: true,
    tabIndex: -1
  });
});
PlaceholderButton.displayName = 'PlaceholderButton';
export default PlaceholderButton;