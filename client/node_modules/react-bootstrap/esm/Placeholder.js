import * as React from 'react';
import usePlaceholder from './usePlaceholder';
import PlaceholderButton from './PlaceholderButton';
import { jsx as _jsx } from "react/jsx-runtime";
const Placeholder = /*#__PURE__*/React.forwardRef(({
  as: Component = 'span',
  ...props
}, ref) => {
  const placeholderProps = usePlaceholder(props);
  return /*#__PURE__*/_jsx(Component, {
    ...placeholderProps,
    ref: ref
  });
});
Placeholder.displayName = 'Placeholder';
export default Object.assign(Placeholder, {
  Button: PlaceholderButton
});