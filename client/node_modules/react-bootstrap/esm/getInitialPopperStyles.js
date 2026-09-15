export default function getInitialPopperStyles(position = 'absolute') {
  return {
    position,
    top: '0',
    left: '0',
    opacity: '0',
    pointerEvents: 'none'
  };
}