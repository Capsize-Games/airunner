"use strict";

exports.__esModule = true;
exports.PROPERTY_PREFIX = exports.ATTRIBUTE_PREFIX = void 0;
exports.dataAttr = dataAttr;
exports.dataProp = dataProp;
const ATTRIBUTE_PREFIX = exports.ATTRIBUTE_PREFIX = `data-rr-ui-`;
const PROPERTY_PREFIX = exports.PROPERTY_PREFIX = `rrUi`;
function dataAttr(property) {
  return `${ATTRIBUTE_PREFIX}${property}`;
}
function dataProp(property) {
  return `${PROPERTY_PREFIX}${property}`;
}