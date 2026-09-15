import * as React from 'react';
export class BsPrefixComponent extends React.Component {}

// Need to use this instead of typeof Component to get proper type checking.

export function getOverlayDirection(placement, isRTL) {
  let bsDirection = placement;
  if (placement === 'left') {
    bsDirection = isRTL ? 'end' : 'start';
  } else if (placement === 'right') {
    bsDirection = isRTL ? 'start' : 'end';
  }
  return bsDirection;
}