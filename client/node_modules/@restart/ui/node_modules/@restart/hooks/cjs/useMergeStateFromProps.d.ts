import { MergeStateSetter } from './useMergeState';
type Mapper<TProps, TState> = (props: TProps, state: TState) => null | Partial<TState>;
export default function useMergeStateFromProps<TProps, TState extends {}>(props: TProps, gDSFP: Mapper<TProps, TState>, initialState: TState): [TState, MergeStateSetter<TState>];
export {};
