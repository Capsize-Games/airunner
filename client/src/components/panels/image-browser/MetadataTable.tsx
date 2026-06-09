import type { ImageInfo } from "../../../api/client";

const separatorColor = "rgba(255,255,255,0.15)";
const rowBorderColor = "rgba(255,255,255,0.08)";

function filterMetadata(img: ImageInfo): [string, unknown][] {
  const version = img.metadata?.version as string | undefined;
  const versionStr = typeof version === "string" ? version.toLowerCase() : "";
  const isSdxlVersion =
    versionStr.includes("sdxl") ||
    versionStr.includes("hyper") ||
    versionStr.includes("lightning");
  const hiddenKeys = [
    "prompt_2", "negative_prompt", "negative_prompt_2",
    "secondary_prompt", "secondary_negative_prompt",
  ];
  return img.metadata
    ? Object.entries(img.metadata).filter(([key]) => isSdxlVersion || !hiddenKeys.includes(key))
    : [];
}

export default function MetadataTable({ img }: { img: ImageInfo }) {
  const metaEntries = filterMetadata(img);

  if (metaEntries.length === 0) {
    return <p style={{ color: "#888", fontSize: 12, textAlign: "center" }}>No metadata</p>;
  }

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
      <thead>
        <tr style={{ background: "rgba(255,255,255,0.06)" }}>
          <th style={{
            padding: "3px 8px 3px 0", textAlign: "left", fontSize: 10,
            textTransform: "uppercase", letterSpacing: 0.5, color: "#aaa",
            fontWeight: 600, borderBottom: `1px solid ${separatorColor}`,
          }}>
            Metadata
          </th>
          <th style={{
            padding: "3px 0", textAlign: "left", fontSize: 10,
            textTransform: "uppercase", letterSpacing: 0.5, color: "#aaa",
            fontWeight: 600, borderBottom: `1px solid ${separatorColor}`,
          }} />
        </tr>
      </thead>
      <tbody>
        {metaEntries.map(([key, value], idx) => {
          const valStr = typeof value === "object" ? JSON.stringify(value) : String(value);
          return (
            <tr key={key} style={{ background: idx % 2 === 0 ? "rgba(255,255,255,0.03)" : "transparent" }}>
              <td style={{
                padding: "2px 8px 2px 0", verticalAlign: "top", whiteSpace: "nowrap",
                color: "#aaa", fontWeight: 600, width: 1, borderBottom: `1px solid ${rowBorderColor}`,
              }}>
                {key}
              </td>
              <td style={{
                padding: "2px 0", verticalAlign: "top", overflow: "hidden",
                textOverflow: "ellipsis", maxWidth: 0, borderBottom: `1px solid ${rowBorderColor}`,
              }} title={valStr}>
                {valStr.length > 120 ? valStr.slice(0, 120) + "..." : valStr}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
