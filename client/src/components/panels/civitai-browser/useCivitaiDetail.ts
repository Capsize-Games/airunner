import { useState, useCallback, useEffect } from "react";
import { fetchCivitaiModel, requestCivitaiVersionThumbnails } from "../../../api/downloads";
import { type JsonObject } from "../../../types/api";
import { useCivitaiDetailCache } from "../../../hooks/useCivitaiDetailCache";
import { useCivitaiThumbnailCache } from "../../../hooks/useCivitaiThumbnailCache";
import { buildModelDetail } from "./civitaiUtils";

export function useCivitaiDetail(
  baseModel: string,
  modelType: string,
  selectedModelId: number | null,
) {
  const detailCache = useCivitaiDetailCache();
  const thumbCache = useCivitaiThumbnailCache();

  const [selectedModelData, setSelectedModelData] = useState<JsonObject | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const applyStreamingThumbnail = useCallback((payload: {
    model_id?: number;
    version_index?: number;
    image_url?: string;
    images_base64?: Record<string, string>;
    model?: JsonObject;
  }) => {
    if (
      payload.model_id === selectedModelId &&
      payload.version_index !== undefined &&
      payload.image_url &&
      payload.images_base64
    ) {
      const vIdx = payload.version_index;
      const imageUrl = payload.image_url;
      const b64Map = payload.images_base64;
      setSelectedModelData((prev) => {
        if (!prev) return prev;
        const versions = [...((prev as JsonObject).modelVersions ?? [])] as JsonObject[];
        if (vIdx >= versions.length) return prev;
        const images = [...((versions[vIdx].images ?? []) as JsonObject[])];
        const iIdx = images.findIndex((img) => (img.url ?? img.thumbnailUrl) === imageUrl);
        if (iIdx < 0) return prev;
        images[iIdx] = { ...images[iIdx], images_base64: b64Map };
        versions[vIdx] = { ...versions[vIdx], images };
        return { ...(prev as JsonObject), modelVersions: versions };
      });
      return;
    }
    if (payload.model && payload.model_id === selectedModelId) {
      setSelectedModelData(payload.model);
    }
  }, [selectedModelId]);

  const fetchModelDetail = useCallback(async (modelId: number) => {
    const cached = await detailCache.get(modelId);
    if (cached) {
      const versions = ((cached.modelVersions ?? []) as JsonObject[]);
      const hydratedVersions = await Promise.all(
        versions.map(async (v, vIdx) => {
          const images = ((v.images ?? []) as JsonObject[]);
          const storedBlobs = await thumbCache.getAll(modelId, vIdx);
          if (Object.keys(storedBlobs).length === 0) return v;
          const hydratedImages = images.map((img) => {
            const imageUrl = String(img.url ?? img.thumbnailUrl ?? "");
            const b64Map = storedBlobs[imageUrl];
            if (!b64Map) return img;
            return { ...img, images_base64: b64Map };
          });
          return { ...v, images: hydratedImages };
        }),
      );
      const hydrated = { ...cached, modelVersions: hydratedVersions };
      setSelectedModelData(hydrated);
      setDetailLoading(false);

      const v0Images = ((hydratedVersions[0]?.images ?? []) as JsonObject[]);
      const hasMissing = v0Images.some((img) => !img.images_base64);
      if (hasMissing) {
        requestCivitaiVersionThumbnails({ model_data: hydrated, version_index: 0 }).catch(() => {});
      }
      return;
    }

    setSelectedModelData({ id: modelId, name: "Loading...", modelVersions: [] } as unknown as JsonObject);
    setDetailLoading(true);
    try {
      const data = await fetchCivitaiModel({
        model_id: String(modelId),
        base_models: baseModel ? [baseModel] : undefined,
        model_types: modelType ? [modelType] : undefined,
      });
      await detailCache.set(modelId, data);
      setSelectedModelData(data);
    } catch {
      setSelectedModelData(null);
    } finally {
      setDetailLoading(false);
    }
  }, [baseModel, modelType, detailCache, thumbCache]);

  const handleRequestVersionThumbnails = useCallback(async (versionId: number) => {
    if (!selectedModelData) return;
    const versions = ((selectedModelData as JsonObject).modelVersions ?? []) as JsonObject[];
    const versionIndex = versions.findIndex((v) => Number(v.id) === versionId);
    if (versionIndex < 0) return;
    try {
      await requestCivitaiVersionThumbnails({ model_data: selectedModelData, version_index: versionIndex });
    } catch { /* */ }
  }, [selectedModelData]);

  useEffect(() => {
    if (selectedModelId === null) return;
    if (baseModel === "" || modelType === "") return;
    fetchModelDetail(selectedModelId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseModel, modelType]);

  const modelDetail = selectedModelData ? buildModelDetail(selectedModelData as JsonObject) : null;

  return {
    selectedModelData, setSelectedModelData,
    detailLoading,
    modelDetail,
    fetchModelDetail,
    handleRequestVersionThumbnails,
    applyStreamingThumbnail,
  };
}
