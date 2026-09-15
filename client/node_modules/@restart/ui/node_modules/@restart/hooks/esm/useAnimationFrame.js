import { useEffect, useState } from 'react';
import useMounted from './useMounted';
/**
 * Returns a controller object for requesting and cancelling an animation frame that is properly cleaned up
 * once the component unmounts. New requests cancel and replace existing ones.
 *
 * ```ts
 * const [style, setStyle] = useState({});
 * const animationFrame = useAnimationFrame();
 *
 * const handleMouseMove = (e) => {
 *   animationFrame.request(() => {
 *     setStyle({ top: e.clientY, left: e.clientY })
 *   })
 * }
 *
 * const handleMouseUp = () => {
 *   animationFrame.cancel()
 * }
 *
 * return (
 *   <div onMouseUp={handleMouseUp} onMouseMove={handleMouseMove}>
 *     <Ball style={style} />
 *   </div>
 * )
 * ```
 */
export default function useAnimationFrame() {
  const isMounted = useMounted();
  const [animationFrame, setAnimationFrameState] = useState(null);
  useEffect(() => {
    if (!animationFrame) {
      return;
    }
    const {
      fn
    } = animationFrame;
    const handle = requestAnimationFrame(fn);
    return () => {
      cancelAnimationFrame(handle);
    };
  }, [animationFrame]);
  const [returnValue] = useState(() => ({
    request(callback) {
      if (!isMounted()) return;
      setAnimationFrameState({
        fn: callback
      });
    },
    cancel: () => {
      if (!isMounted()) return;
      setAnimationFrameState(null);
    }
  }));
  return returnValue;
}