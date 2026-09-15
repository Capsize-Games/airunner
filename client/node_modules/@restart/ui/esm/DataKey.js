export const ATTRIBUTE_PREFIX = `data-rr-ui-`;
export const PROPERTY_PREFIX = `rrUi`;
export function dataAttr(property) {
  return `${ATTRIBUTE_PREFIX}${property}`;
}
export function dataProp(property) {
  return `${PROPERTY_PREFIX}${property}`;
}