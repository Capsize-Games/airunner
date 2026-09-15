"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault");
exports.__esModule = true;
exports.default = void 0;
var _propTypes = _interopRequireDefault(require("prop-types"));
var _TabContainer = _interopRequireDefault(require("./TabContainer"));
var _TabContent = _interopRequireDefault(require("./TabContent"));
var _TabPane = _interopRequireDefault(require("./TabPane"));
const propTypes = {
  eventKey: _propTypes.default.oneOfType([_propTypes.default.string, _propTypes.default.number]),
  /**
   * Content for the tab title.
   */
  title: _propTypes.default.node.isRequired,
  /**
   * The disabled state of the tab.
   */
  disabled: _propTypes.default.bool,
  /**
   * Class to pass to the underlying nav link.
   */
  tabClassName: _propTypes.default.string,
  /**
   * Object containing attributes to pass to underlying nav link.
   */
  tabAttrs: _propTypes.default.object
};
const Tab = () => {
  throw new Error('ReactBootstrap: The `Tab` component is not meant to be rendered! ' + "It's an abstract component that is only valid as a direct Child of the `Tabs` Component. " + 'For custom tabs components use TabPane and TabsContainer directly');
};
Tab.propTypes = propTypes;
var _default = exports.default = Object.assign(Tab, {
  Container: _TabContainer.default,
  Content: _TabContent.default,
  Pane: _TabPane.default
});
module.exports = exports.default;