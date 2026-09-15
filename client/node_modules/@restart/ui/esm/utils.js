import * as React from 'react';
export function isEscKey(e) {
  return e.code === 'Escape' || e.keyCode === 27;
}
export function getReactVersion() {
  const parts = React.version.split('.');
  return {
    major: +parts[0],
    minor: +parts[1],
    patch: +parts[2]
  };
}
export function getChildRef(element) {
  if (!element || typeof element === 'function') {
    return null;
  }
  const {
    major
  } = getReactVersion();
  const childRef = major >= 19 ? element.props.ref : element.ref;
  return childRef;
}