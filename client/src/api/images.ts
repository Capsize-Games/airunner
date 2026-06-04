import { request } from "./client-base";

export interface ImageDateInfo {
  value: string;
  label: string;
}

export interface ImageInfo {
  id: string;
  image_url: string;
  thumbnail_url: string;
  file_path: string;
  file_size: number;
  file_timestamp: number;
  metadata: Record<string, unknown> | null;
}

export interface ImageInfoResponse extends ImageInfo {
  // Same fields as ImageInfo, returned by the info endpoint.
}

export interface ListImageDatesResponse {
  dates: ImageDateInfo[];
}

export interface ListImagesResponse {
  total: number;
  images: ImageInfo[];
}

export async function listImageDates() {
  return request<ListImageDatesResponse>("GET", "/api/v1/art/images/dates");
}

export async function listImages(
  date: string,
  offset = 0,
  limit = 20,
) {
  return request<ListImagesResponse>(
    "GET",
    `/api/v1/art/images/${date}?offset=${offset}&limit=${limit}`,
  );
}

export async function getImageInfo(
  date: string,
  filename: string,
) {
  return request<ImageInfoResponse>(
    "GET",
    `/api/v1/art/images/${date}/info/${filename}`,
  );
}

export async function deleteImage(date: string, filename: string) {
  return request<{ success: boolean; deleted: string }>(
    "DELETE", `/api/v1/art/images/${date}/delete/${filename}`,
  );
}

export async function renameImage(
  date: string, oldFilename: string, newFilename: string,
) {
  return request<{ success: boolean; new_id: string }>(
    "PUT", `/api/v1/art/images/${date}/rename/${oldFilename}`,
    { new_filename: newFilename },
  );
}
