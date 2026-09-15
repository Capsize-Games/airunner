"use strict";

exports.__esModule = true;
exports.default = useMergeStateFromProps;
var _useMergeState = _interopRequireDefault(require("./useMergeState"));
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function useMergeStateFromProps(props, gDSFP, initialState) {
  const [state, setState] = (0, _useMergeState.default)(initialState);
  const nextState = gDSFP(props, state);
  if (nextState !== null) setState(nextState);
  return [state, setState];
}