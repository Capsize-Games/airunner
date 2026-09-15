import NoopTransition from '@restart/ui/NoopTransition';
import Fade from './Fade';
export default function getTabTransitionComponent(transition) {
  if (typeof transition === 'boolean') {
    return transition ? Fade : NoopTransition;
  }
  return transition;
}