import classNames from 'classnames';
import * as React from 'react';
import Image, { propTypes as imagePropTypes } from './Image';
import { jsx as _jsx } from "react/jsx-runtime";
const FigureImage = /*#__PURE__*/React.forwardRef(({
  className,
  fluid = true,
  ...props
}, ref) => /*#__PURE__*/_jsx(Image, {
  ref: ref,
  ...props,
  fluid: fluid,
  className: classNames(className, 'figure-img')
}));
FigureImage.displayName = 'FigureImage';
FigureImage.propTypes = imagePropTypes;
export default FigureImage;