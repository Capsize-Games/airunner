import * as React from 'react';
const SelectableContext = /*#__PURE__*/React.createContext(null);
export const makeEventKey = (eventKey, href = null) => {
  if (eventKey != null) return String(eventKey);
  return href || null;
};
export default SelectableContext;