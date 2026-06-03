/** Shared types for the CivitAI model detail components. */

export interface VersionImage {
  url: string;
  nsfw?: string;
  width?: number;
  height?: number;
  /** Inline base64 images from the server, keyed by size. */
  images_base64?: Record<string, string>;
}

export interface CivitaiFile {
  id: number;
  name: string;
  sizeKB?: number;
  downloadUrl?: string;
  /** Server sets this to true when the file already exists on disk. */
  downloaded?: boolean;
}

export interface CivitaiVersion {
  id: number;
  name: string;
  baseModel?: string;
  files?: CivitaiFile[];
  images?: VersionImage[];
  downloadUrl?: string;
}

export interface ModelDetailData {
  id: number;
  name: string;
  description?: string;
  creator?: string;
  type?: string;
  stats?: { downloadCount?: number; favoriteCount?: number; commentCount?: number };
  versions?: CivitaiVersion[];
  allowNoCredit?: boolean;
  allowCommercialUse?: string;
  allowDerivatives?: string;
  allowDifferentLicense?: boolean;
}
