import PropTypes from 'prop-types';
const alignDirection = PropTypes.oneOf(['start', 'end']);
export const alignPropType = PropTypes.oneOfType([alignDirection, PropTypes.shape({
  sm: alignDirection
}), PropTypes.shape({
  md: alignDirection
}), PropTypes.shape({
  lg: alignDirection
}), PropTypes.shape({
  xl: alignDirection
}), PropTypes.shape({
  xxl: alignDirection
}), PropTypes.object]);