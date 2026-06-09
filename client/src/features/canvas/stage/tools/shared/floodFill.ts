// ── Shared Flood-Fill Algorithm ────────────────────────────────────────────
// A single pure BFS flood fill used by both the Fuzzy Select (magic wand)
// and Bucket Fill tools.  It computes a boolean selection mask from a seed
// point and a color tolerance; it never mutates the source pixels.
//
// Consumers use the mask differently:
//   • Fuzzy Select → trace the mask boundary for a marching-ants outline.
//   • Bucket Fill  → write the fill color over every masked pixel.

export interface FloodFillOptions {
  /** Use 8-connectivity (include diagonals) instead of 4-connectivity. */
  diagonal?: boolean;
  /** If true, fully transparent (alpha=0) pixels are matchable. */
  matchTransparent?: boolean;
}

/** RGBA Euclidean distance between two pixels in an ImageData byte array. */
export function colorDistance(
  data: Uint8ClampedArray,
  i1: number,
  i2: number,
): number {
  const dr = data[i1] - data[i2];
  const dg = data[i1 + 1] - data[i2 + 1];
  const db = data[i1 + 2] - data[i2 + 2];
  const da = data[i1 + 3] - data[i2 + 3];
  return Math.sqrt(dr * dr + dg * dg + db * db + da * da);
}

/**
 * Convert a 0–100 threshold slider value to an RGBA Euclidean distance.
 * 100 maps to the maximum possible distance, sqrt(255² × 4) ≈ 441.67.
 */
export function thresholdToDistance(t: number): number {
  return (t / 100) * Math.sqrt(255 * 255 * 4);
}

/**
 * Breadth-First Search flood fill returning a boolean mask (Uint8Array).
 *
 * The mask has length width*height; 1 = selected.  Pixels are matched by
 * comparing each candidate against the *seed* pixel's color (captured before
 * traversal) — never against the previously visited pixel, which would cause
 * color drift across the image.
 *
 * @param imageData  Raw pixel data (width × height × 4).
 * @param startX     Seed x in image-local pixel coordinates.
 * @param startY     Seed y in image-local pixel coordinates.
 * @param tolerance  Max RGBA Euclidean distance for inclusion (see
 *                   {@link thresholdToDistance}).
 * @param options    Connectivity and transparency behavior.
 */
export function floodFillMask(
  imageData: ImageData,
  startX: number,
  startY: number,
  tolerance: number,
  options: FloodFillOptions = {},
): Uint8Array {
  const { diagonal = false, matchTransparent = false } = options;
  const { width, height, data } = imageData;
  const size = width * height;
  const mask = new Uint8Array(size);

  const sx = Math.round(startX);
  const sy = Math.round(startY);
  if (sx < 0 || sx >= width || sy < 0 || sy >= height) return mask;

  const startIdx = (sy * width + sx) * 4;

  // Capture the seed color up front so the comparison reference is stable
  // even if a caller later mutates the pixel data.
  const seedR = data[startIdx];
  const seedG = data[startIdx + 1];
  const seedB = data[startIdx + 2];
  const seedA = data[startIdx + 3];
  const clickedTransparent = seedA === 0;

  // Clicking a transparent pixel when transparency isn't matchable does
  // nothing.
  if (clickedTransparent && !matchTransparent) return mask;

  const visited = new Uint8Array(size);
  const queue = new Int32Array(size * 2);
  let head = 0;
  let tail = 0;

  const startPixel = sy * width + sx;
  visited[startPixel] = 1;
  mask[startPixel] = 1;
  queue[tail++] = sx;
  queue[tail++] = sy;

  // Neighbor offsets (4- or 8-connectivity).
  const dx = diagonal
    ? [0, 1, 1, 1, 0, -1, -1, -1]
    : [0, 1, 0, -1];
  const dy = diagonal
    ? [-1, -1, 0, 1, 1, 1, 0, -1]
    : [-1, 0, 1, 0];
  const dirs = dx.length;

  while (head < tail) {
    const cx = queue[head++];
    const cy = queue[head++];

    for (let d = 0; d < dirs; d++) {
      const nx = cx + dx[d];
      const ny = cy + dy[d];

      if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;

      const np = ny * width + nx;
      if (visited[np]) continue;
      visited[np] = 1;

      const ni = np * 4;

      // Hard boundary: when transparency isn't matchable, any fully
      // transparent pixel stops the fill.
      if (!matchTransparent && data[ni + 3] === 0) continue;

      if (clickedTransparent) {
        // Seed was transparent — match only other fully transparent pixels.
        if (data[ni + 3] !== 0) continue;
      } else {
        // Compare against the seed color (not the current pixel).
        const dr = seedR - data[ni];
        const dg = seedG - data[ni + 1];
        const db = seedB - data[ni + 2];
        const da = seedA - data[ni + 3];
        const dist = Math.sqrt(dr * dr + dg * dg + db * db + da * da);
        if (dist > tolerance) continue;
      }

      mask[np] = 1;
      queue[tail++] = nx;
      queue[tail++] = ny;
    }
  }

  return mask;
}
