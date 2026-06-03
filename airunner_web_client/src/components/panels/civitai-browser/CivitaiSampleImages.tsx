import { useState } from "react";
import CivitaiImage from "./CivitaiImage";

interface CivitaiImageInfo {
  url: string;
  nsfw?: string;
  width?: number;
  height?: number;
}

interface CivitaiSampleImagesProps {
  images: CivitaiImageInfo[];
}

export default function CivitaiSampleImages({
  images,
}: CivitaiSampleImagesProps) {
  const [selectedUrl, setSelectedUrl] = useState<string | null>(
    images.length > 0 ? images[0].url : null,
  );

  if (!images || images.length === 0) return null;

  const preview = images.find((img) => img.url === selectedUrl);

  return (
    <div className="mb-2">
      <small className="text-muted d-block mb-1">Sample Images</small>

      {/* Preview */}
      {preview && (
        <div
          style={{
            width: "100%",
            height: 120,
            borderRadius: 4,
            overflow: "hidden",
            marginBottom: 4,
            background: "var(--theme-bg-secondary)",
          }}
        >
          <CivitaiImage
            url={preview.url}
            alt="Preview"
            thumbWidth={400}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
            }}
          />
        </div>
      )}

      {/* Thumbnail strip */}
      <div
        style={{
          display: "flex",
          gap: 4,
          overflowX: "auto",
          paddingBottom: 2,
        }}
      >
        {images.slice(0, 10).map((img) => (
          <div
            key={img.url}
            onClick={() => setSelectedUrl(img.url)}
            style={{
              width: 48,
              height: 48,
              borderRadius: 4,
              overflow: "hidden",
              cursor: "pointer",
              flexShrink: 0,
              border:
                selectedUrl === img.url
                  ? "2px solid var(--bs-primary)"
                  : "2px solid transparent",
            }}
          >
            <CivitaiImage
              url={img.url}
              alt="Thumb"
              thumbWidth={48}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
