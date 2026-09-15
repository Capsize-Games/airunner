import * as React from 'react';
import invariant from 'invariant';
import { useUncontrolled } from 'uncontrollable';
import chainFunction from './createChainedFunction';
import { map } from './ElementChildren';
import ButtonGroup from './ButtonGroup';
import ToggleButton from './ToggleButton';
import { jsx as _jsx } from "react/jsx-runtime";
const ToggleButtonGroup = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    children,
    type = 'radio',
    name,
    value,
    onChange,
    vertical = false,
    ...controlledProps
  } = useUncontrolled(props, {
    value: 'onChange'
  });
  const getValues = () => value == null ? [] : [].concat(value);
  const handleToggle = (inputVal, event) => {
    if (!onChange) {
      return;
    }
    const values = getValues();
    const isActive = values.indexOf(inputVal) !== -1;
    if (type === 'radio') {
      if (!isActive) onChange(inputVal, event);
      return;
    }
    if (isActive) {
      onChange(values.filter(n => n !== inputVal), event);
    } else {
      onChange([...values, inputVal], event);
    }
  };
  !(type !== 'radio' || !!name) ? process.env.NODE_ENV !== "production" ? invariant(false, 'A `name` is required to group the toggle buttons when the `type` ' + 'is set to "radio"') : invariant(false) : void 0;
  return /*#__PURE__*/_jsx(ButtonGroup, {
    ...controlledProps,
    ref: ref,
    vertical: vertical,
    children: map(children, child => {
      const values = getValues();
      const {
        value: childVal,
        onChange: childOnChange
      } = child.props;
      const handler = e => handleToggle(childVal, e);
      return /*#__PURE__*/React.cloneElement(child, {
        type,
        name: child.name || name,
        checked: values.indexOf(childVal) !== -1,
        onChange: chainFunction(childOnChange, handler)
      });
    })
  });
});
ToggleButtonGroup.displayName = 'ToggleButtonGroup';
export default Object.assign(ToggleButtonGroup, {
  Button: ToggleButton
});