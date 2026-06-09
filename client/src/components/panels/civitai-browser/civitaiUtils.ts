import { type JsonObject } from "../../../types/api";
import { MODEL_TYPE_OPTIONS } from "./constants";
import { request } from "../../../api/client-base";

export interface SearchResult {
  id: number; name: string; type?: string; baseModel?: string;
  creator?: string; thumbnail?: string;
  thumbnails?: Record<string, string>;
}

export interface FilterOption { label: string; value: string; }

export function flattenItem(item: JsonObject): SearchResult {
  const creatorObj = item.creator as JsonObject | undefined;
  const creatorName = creatorObj?.username ? String(creatorObj.username) : String(item.creator ?? "Unknown");
  const versions = (item.modelVersions ?? []) as JsonObject[];
  let thumbUrl = "";
  if (versions.length > 0) {
    const images = (versions[0].images ?? []) as JsonObject[];
    if (images.length > 0) thumbUrl = String(images[0].url ?? images[0].thumbnailUrl ?? "");
  }
  if (!thumbUrl) thumbUrl = String((item as JsonObject).image ?? "");
  return {
    id: Number(item.id), name: String(item.name ?? ""),
    type: item.type ? String(item.type) : undefined,
    baseModel: item.baseModel ? String(item.baseModel) : undefined,
    creator: creatorName,
    thumbnail: thumbUrl || undefined,
    thumbnails: (item.thumbnails as Record<string, string> | undefined) || undefined,
  };
}

export async function fetchFilterOptions(): Promise<{ baseModels: FilterOption[]; modelTypes: string[]; typesByBase: Record<string, string[]> }> {
  const data = await request<{ base_models: FilterOption[]; model_types: string[]; model_types_by_base: Record<string, string[]> }>(
    "GET", "/api/v1/downloads/civitai/options",
  );
  const baseModels: FilterOption[] = data.base_models ?? [];
  const modelTypes: string[] = data.model_types ?? [];
  let typesByBase = data.model_types_by_base ?? {};
  if (Object.keys(typesByBase).length === 0 && baseModels.length > 0) {
    typesByBase = {};
    for (const bm of baseModels) {
      const types = MODEL_TYPE_OPTIONS[bm.value];
      if (types) typesByBase[bm.value] = types.map((t) => t.value);
    }
  }
  return { baseModels, modelTypes, typesByBase };
}

export function buildModelDetail(selectedModelData: JsonObject) {
  const raw = selectedModelData;
  const creatorObj = raw.creator as JsonObject | undefined;
  const creatorName = creatorObj?.username ? String(creatorObj.username) : String(raw.creator ?? "Unknown");
  const versions = (raw.modelVersions ?? []) as JsonObject[];
  return {
    id: Number(raw.id ?? 0), name: String(raw.name ?? ""),
    description: raw.description ? String(raw.description) : undefined,
    creator: creatorName, type: raw.type ? String(raw.type) : undefined,
    stats: raw.stats as { downloadCount?: number; favoriteCount?: number; commentCount?: number } | undefined,
    allowNoCredit: raw.allowNoCredit === true,
    allowCommercialUse: raw.allowCommercialUse === true ? "Commercial" : (raw.allowCommercialUse === false ? "Non-Commercial" : undefined),
    allowDerivatives: raw.allowDerivatives === true ? "Allowed" : (raw.allowDerivatives === false ? "Not allowed" : undefined),
    allowDifferentLicense: raw.allowDifferentLicense === true,
    versions: versions.map((v: JsonObject) => ({
      id: Number(v.id), name: String(v.name ?? ""),
      baseModel: v.baseModel ? String(v.baseModel) : undefined,
      files: ((v.files ?? []) as JsonObject[]).map((f: JsonObject) => ({
        id: Number(f.id), name: String(f.name ?? ""),
        sizeKB: f.sizeKB ? Number(f.sizeKB) : undefined,
        downloadUrl: f.downloadUrl ? String(f.downloadUrl) : undefined,
        downloaded: f.downloaded === true,
      })),
      images: ((v.images ?? []) as JsonObject[]).map((img: JsonObject) => ({
        url: String(img.url ?? img.thumbnailUrl ?? ""),
        nsfw: img.nsfw ? String(img.nsfw) : undefined,
        width: img.width ? Number(img.width) : undefined,
        height: img.height ? Number(img.height) : undefined,
        images_base64: (img.images_base64 as Record<string, string> | undefined) || undefined,
      })),
    })),
  };
}
