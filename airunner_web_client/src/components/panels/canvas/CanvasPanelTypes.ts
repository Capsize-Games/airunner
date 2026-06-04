/** Pending image-drop payload awaiting resize-mode selection. */
export interface PendingDrop {
  base64: string;
  x: number;
  y: number;
  naturalW: number;
  naturalH: number;
}

/** Magic-byte signatures for common image formats. */
export const IMAGE_MAGIC: [number[], number][] = [
  [[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A], 8], // PNG
  [[0xFF, 0xD8, 0xFF],                                     3], // JPEG
  [[0x47, 0x49, 0x46, 0x38],                               4], // GIF87a / GIF89a
  [[0x42, 0x4D],                                            2], // BMP
];
