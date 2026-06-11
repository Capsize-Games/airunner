// ── Marching Ants Animation ───────────────────────────────────────────────
// Returns a continuously decreasing dash offset (in canvas px) that, when fed
// to a dashed Konva stroke's `dashOffset`, animates the dashes so they appear
// to "march" along the path — the classic selection-marquee effect.

import { useEffect, useState } from "react";

/**
 * @param speed Dash travel speed in px/ms (default ≈ 40 px/s).
 * @returns The current dash offset to pass to a shape's `dashOffset`.
 */
export function useMarchingAnts(speed = 0.04): number {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    let raf = 0;
    let start = 0;
    const tick = (t: number) => {
      if (!start) start = t;
      // Negative so the ants march "forward" along the path direction.
      setOffset(-((t - start) * speed));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [speed]);

  return offset;
}
