import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../../api/client";

interface MetadataFlags {
  prompt: boolean;
  negative_prompt: boolean;
  samples: boolean;
  model: boolean;
  model_branch: boolean;
  scale: boolean;
  seed: boolean;
  steps: boolean;
  iterations: boolean;
  scheduler: boolean;
  ddim_eta: boolean;
  strength: boolean;
  clip_skip: boolean;
  version: boolean;
  lora: boolean;
  embeddings: boolean;
  timestamp: boolean;
  controlnet: boolean;
  tome_sd: boolean;
  tome_ratio: boolean;
}

const DEFAULT_METADATA_FLAGS: MetadataFlags = {
  prompt: true,
  negative_prompt: true,
  samples: true,
  model: true,
  model_branch: true,
  scale: true,
  seed: true,
  steps: true,
  iterations: true,
  scheduler: true,
  ddim_eta: true,
  strength: true,
  clip_skip: true,
  version: true,
  lora: true,
  embeddings: true,
  timestamp: true,
  controlnet: true,
  tome_sd: true,
  tome_ratio: true,
};

const METADATA_LABELS: Record<keyof MetadataFlags, string> = {
  prompt: "Prompt",
  negative_prompt: "Negative Prompt",
  samples: "Samples",
  model: "Model",
  model_branch: "Model Branch",
  scale: "Scale",
  seed: "Seed",
  steps: "Steps",
  iterations: "Iterations",
  scheduler: "Scheduler",
  ddim_eta: "DDIM ETA",
  strength: "Strength",
  clip_skip: "Clip Skip",
  version: "Version",
  lora: "LoRA",
  embeddings: "Embeddings",
  timestamp: "Timestamp",
  controlnet: "Controlnet",
  tome_sd: "ToMe SD",
  tome_ratio: "ToMe Ratio",
};

export default function ImageExportSection() {
  const [loading, setLoading] = useState(true);
  const [storeInDb, setStoreInDb] = useState(true);
  const [storeLocally, setStoreLocally] = useState(true);
  const [autoExport, setAutoExport] = useState(true);
  const [exportType, setExportType] = useState("png");
  const [exportFolder, setExportFolder] = useState("");
  const [exportMetadata, setExportMetadata] = useState(true);
  const [metadataFlags, setMetadataFlags] = useState<MetadataFlags>(
    DEFAULT_METADATA_FLAGS,
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const appSettings = await getSingleton("ApplicationSettings");
        if (cancelled) return;
        setStoreInDb(appSettings.store_images_in_db !== false);
        setStoreLocally(appSettings.store_images_locally !== false);
        setAutoExport(appSettings.auto_export_images !== false);
        setExportType(String(appSettings.image_export_type ?? "png"));
        setExportFolder(String(appSettings.image_export_folder ?? ""));
        setExportMetadata(appSettings.export_metadata_enabled !== false);

        const rawFlags = appSettings.metadata_export_flags;
        if (rawFlags && typeof rawFlags === "string") {
          try {
            const parsed = JSON.parse(rawFlags);
            setMetadataFlags({ ...DEFAULT_METADATA_FLAGS, ...parsed });
          } catch {
            setMetadataFlags(DEFAULT_METADATA_FLAGS);
          }
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function persist(overrides: Record<string, unknown>) {
    const payload: Record<string, unknown> = {
      store_images_in_db: storeInDb,
      store_images_locally: storeLocally,
      auto_export_images: autoExport,
      image_export_type: exportType,
      image_export_folder: exportFolder,
      export_metadata_enabled: exportMetadata,
      metadata_export_flags: JSON.stringify(metadataFlags),
      ...overrides,
    };
    updateSingleton("ApplicationSettings", payload).catch(() => {});
  }

  function handleToggleStoreInDb(checked: boolean) {
    setStoreInDb(checked);
    persist({ store_images_in_db: checked });
  }

  function handleToggleStoreLocally(checked: boolean) {
    setStoreLocally(checked);
    persist({ store_images_locally: checked });
  }

  function handleToggleAutoExport(checked: boolean) {
    setAutoExport(checked);
    persist({ auto_export_images: checked });
  }

  function handleExportTypeChange(value: string) {
    setExportType(value);
    persist({ image_export_type: value });
  }

  function handleExportFolderChange(value: string) {
    setExportFolder(value);
    persist({ image_export_folder: value });
  }

  function handleToggleExportMetadata(checked: boolean) {
    setExportMetadata(checked);
    persist({ export_metadata_enabled: checked });
  }

  function handleMetadataFlag(
    key: keyof MetadataFlags,
    checked: boolean,
  ) {
    const updated = { ...metadataFlags, [key]: checked };
    setMetadataFlags(updated);
    persist({ metadata_export_flags: JSON.stringify(updated) });
  }

  if (loading) {
    return (
      <div className="text-center py-4">
        <Spinner animation="border" size="sm" />
      </div>
    );
  }

  const metaKeys = Object.keys(METADATA_LABELS) as Array<keyof MetadataFlags>;

  return (
    <div>
      <h6 className="mb-3">Image Export</h6>

      {/* Saving group */}
      <Form.Label className="small text-muted fw-semibold mb-1">
        Saving
      </Form.Label>

      <Form.Group className="mb-1">
        <Form.Check
          type="switch"
          label="Store images in database"
          checked={storeInDb}
          onChange={(e) => handleToggleStoreInDb(e.target.checked)}
          className="small"
        />
      </Form.Group>

      <Form.Group className="mb-1">
        <Form.Check
          type="switch"
          label="Store generated images to disk"
          checked={storeLocally}
          onChange={(e) => handleToggleStoreLocally(e.target.checked)}
          className="small"
        />
      </Form.Group>

      <Form.Group className="mb-1">
        <Form.Check
          type="switch"
          label="Automatically export images"
          checked={autoExport}
          onChange={(e) => handleToggleAutoExport(e.target.checked)}
          className="small"
        />
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Label className="small">Image export folder</Form.Label>
        <div className="d-flex gap-1">
          <Form.Control
            size="sm"
            type="text"
            value={exportFolder}
            onChange={(e) => handleExportFolderChange(e.target.value)}
            placeholder="Leave empty for default"
            className="bg-dark text-light border-secondary"
          />
        </div>
      </Form.Group>

      <Form.Group className="mb-3">
        <Form.Label className="small">Image type</Form.Label>
        <Form.Select
          size="sm"
          value={exportType}
          onChange={(e) => handleExportTypeChange(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="png">PNG</option>
          <option value="jpeg">JPEG</option>
          <option value="webp">WebP</option>
        </Form.Select>
      </Form.Group>

      {/* Export Metadata group */}
      <Form.Label className="small text-muted fw-semibold mb-1">
        <Form.Check
          type="switch"
          id="export-metadata-toggle"
          label="Export Metadata"
          checked={exportMetadata}
          onChange={(e) => handleToggleExportMetadata(e.target.checked)}
          className="small d-inline-flex align-items-center gap-1"
          style={{ fontWeight: 600 }}
        />
      </Form.Label>

      {exportMetadata && (
        <div
          className="border rounded p-2 mb-2"
          style={{ maxHeight: 280, overflowY: "auto" }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "2px 12px",
            }}
          >
            {metaKeys.map((key) => (
              <Form.Check
                key={key}
                type="switch"
                id={`meta-${key}`}
                label={METADATA_LABELS[key]}
                checked={metadataFlags[key]}
                onChange={(e) =>
                  handleMetadataFlag(key, e.target.checked)
                }
                className="small"
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
