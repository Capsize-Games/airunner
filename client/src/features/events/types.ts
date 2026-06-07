/** Event bus protocol types for the unified /api/v1/events WebSocket. */

/** Client → Server messages. */
export interface WsSubscribeMessage {
  type: "subscribe";
  events: string[];
}

export interface WsUnsubscribeMessage {
  type: "unsubscribe";
  events: string[];
}

export interface WsPingMessage {
  type: "ping";
}

export type WsClientMessage =
  | WsSubscribeMessage
  | WsUnsubscribeMessage
  | WsPingMessage;

/** Server → Client messages. */
export interface WsEventMessage {
  type: "event";
  event: string;
  data: unknown;
}

export interface WsKeepaliveMessage {
  type: "keepalive";
}

export interface WsSubscribedMessage {
  type: "subscribed";
  events: string[];
}

export interface WsUnsubscribedMessage {
  type: "unsubscribed";
  events: string[];
}

export interface WsPongMessage {
  type: "pong";
}

export type WsServerMessage =
  | WsEventMessage
  | WsKeepaliveMessage
  | WsSubscribedMessage
  | WsUnsubscribedMessage
  | WsPongMessage;

/** Supported event type constants — mirror server-side ALL_EVENTS. */
export const EVENT_IMAGES = "images";
export const EVENT_LORAS = "loras";
export const EVENT_EMBEDDINGS = "embeddings";
export const EVENT_DOCUMENTS = "documents";
export const EVENT_MODEL_STATUS = "model_status";
export const EVENT_INDEX_PROGRESS = "index_progress";
export const EVENT_DOWNLOADS = "downloads";
export const EVENT_CIVITAI_THUMBNAIL = "civitai_thumbnail";
