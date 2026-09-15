"use client";

import * as React from 'react';
export function isAccordionItemSelected(activeEventKey, eventKey) {
  return Array.isArray(activeEventKey) ? activeEventKey.includes(eventKey) : activeEventKey === eventKey;
}
const context = /*#__PURE__*/React.createContext({});
context.displayName = 'AccordionContext';
export default context;