/** Server URL — empty string when proxied through Vite dev server,
 *  otherwise configurable via env or defaults to localhost:8188. */
export const BASE_URL = import.meta.env.PROD
  ? (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8188")
  : "";

/** Generic JSON response wrapper. */
export type JsonObject = Record<string, unknown>;

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------
export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  thinking_content?: string;
  created_at?: string;
}

export interface Conversation {
  id: number;
  title: string;
  current: boolean;
  messages?: Message[];
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: Conversation[];
}

export interface ConversationSessionResponse {
  conversation_id?: number;
  messages: Record<string, unknown>[];
}

// ---------------------------------------------------------------------------
// Hardware
// ---------------------------------------------------------------------------
export interface HardwareProfile {
  total_vram_gb: number;
  available_vram_gb: number;
  total_ram_gb: number;
  available_ram_gb: number;
  cuda_available: boolean;
  device_name: string | null;
  cpu_count: number;
  platform: string;
}

// ---------------------------------------------------------------------------
// LLM / Chat
// ---------------------------------------------------------------------------
export interface ChatCompletionRequest {
  messages: Message[];
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface StreamChunk {
  token?: string;
  done?: boolean;
  message_type?: string;
  conversation_id?: number;
  error?: string;
}

// ---------------------------------------------------------------------------
// Art
// ---------------------------------------------------------------------------
export interface ArtGenerateRequest {
  prompt: string;
  negative_prompt?: string;
  width?: number;
  height?: number;
  steps?: number;
  cfg_scale?: number;
  seed?: number;
  num_images?: number;
  model?: string;
  version?: string;
  scheduler?: string;
}

export interface ArtGenerateResponse {
  job_id: string;
}

export interface ArtJobStatus {
  status: string;
  progress: number;
  error?: string;
}

// ---------------------------------------------------------------------------
// VRAM
// ---------------------------------------------------------------------------
export interface VRAMEstimate {
  path: string;
  file_size_gb: number;
  native_dtype: string | null;
}

// ---------------------------------------------------------------------------
// Bootstrap / Catalog
// ---------------------------------------------------------------------------
export interface BootstrapData {
  models: JsonObject[];
  pipelines: JsonObject[];
  unified_model_files: JsonObject;
  controlnet_bootstrap_data: JsonObject[];
  espeak_settings_data: JsonObject[];
  llm_file_bootstrap_data: JsonObject;
  openvoice_files: JsonObject;
  openvoice_core_models: JsonObject[];
  openvoice_language_models: JsonObject;
  path_settings_data: JsonObject[];
  rmbg_files: JsonObject;
  sd_file_bootstrap_data: JsonObject;
  whisper_files: JsonObject;
  imagefilter_bootstrap_data: JsonObject;
  prompt_templates_bootstrap_data: JsonObject[];
}

// ---------------------------------------------------------------------------
// Settings (resource store)
// ---------------------------------------------------------------------------
export interface ResourceRecord {
  id?: number;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Downloads
// ---------------------------------------------------------------------------
export interface DownloadJobAccepted {
  job_id: string;
  status?: string;
}

export interface DownloadJobStatus {
  status: string;
  progress: number;
  error?: string;
  result?: JsonObject;
  metadata?: JsonObject;
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------
export interface DocumentRecord {
  id: number;
  name: string;
  path: string;
  file_type: string;
  indexed: boolean;
  active: boolean;
}
