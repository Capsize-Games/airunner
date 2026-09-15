import useMergeState from './useMergeState';
export default function useMergeStateFromProps(props, gDSFP, initialState) {
  const [state, setState] = useMergeState(initialState);
  const nextState = gDSFP(props, state);
  if (nextState !== null) setState(nextState);
  return [state, setState];
}