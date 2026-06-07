import Dexie, { type Table } from "dexie";
import type { Conversation, Message, DocumentRecord } from "../types/api";
import type { LoraInfo } from "../api/loras";
import type { EmbeddingInfo } from "../api/embeddings";

// ── Stored record shapes ─────────────────────────────────────────────────────

export interface CachedConversation extends Omit<Conversation, "messages"> {
  cachedAt: number;
}

export interface CachedMessage extends Message {
  id: string;           // `${conversationId}_${index}` — stable key
  conversationId: number;
  sortIndex: number;    // preserves server order
}

export interface CachedLora extends LoraInfo {
  cachedAt: number;
}

export interface CachedEmbedding extends EmbeddingInfo {
  cachedAt: number;
}

export interface CachedKbDocument extends DocumentRecord {
  cachedAt: number;
}

export interface CachedCivitaiModel {
  id: number;
  data: Record<string, unknown>;
  cachedAt: number;
}

export interface CachedCivitaiThumbnail {
  key: string;   // `${modelId}_${versionIndex}_${imageUrl}`
  blob: string;  // base64 data URL
  cachedAt: number;
}

export interface CachedCanvasDocument {
  id: string;    // always "default" for this app
  documentJson: string;
  updatedAt: number;
}

export interface CachedImageDate {
  date: string;
  cachedAt: number;
}

export interface CachedImage {
  id: string;    // `${date}__${filename}`
  date: string;
  imageUrl: string;
  thumbnailUrl: string;
  fileSize: number;
  fileTimestamp: number;
  metadata: Record<string, unknown> | null;
  cachedAt: number;
}

// ── Dexie database class ─────────────────────────────────────────────────────

class AiRunnerDb extends Dexie {
  conversations!: Table<CachedConversation, number>;
  messages!: Table<CachedMessage, string>;
  loras!: Table<CachedLora, number>;
  embeddings!: Table<CachedEmbedding, number>;
  kbDocuments!: Table<CachedKbDocument, number>;
  civitaiModels!: Table<CachedCivitaiModel, number>;
  civitaiThumbnails!: Table<CachedCivitaiThumbnail, string>;
  canvasDocuments!: Table<CachedCanvasDocument, string>;
  imageDates!: Table<CachedImageDate, string>;
  images!: Table<CachedImage, string>;

  constructor() {
    super("airunner");
    this.version(1).stores({
      conversations:    "id, updatedAt, current, cachedAt",
      messages:         "id, conversationId, sortIndex",
      loras:            "id, path, enabled, cachedAt",
      embeddings:       "id, path, enabled, cachedAt",
      kbDocuments:      "id, active, indexed, cachedAt",
      civitaiModels:    "id, cachedAt",
      civitaiThumbnails:"key, cachedAt",
      canvasDocuments:  "id, updatedAt",
      imageDates:       "date, cachedAt",
      images:           "id, date, cachedAt",
    });
  }
}

// ── Singleton instance ────────────────────────────────────────────────────────

let _db: AiRunnerDb | null = null;

export function getDb(): AiRunnerDb | null {
  if (_db) return _db;
  try {
    _db = new AiRunnerDb();
    return _db;
  } catch {
    return null;
  }
}

export type { AiRunnerDb };
