export interface LiveStrokeMessage {
  type: "stroke:live";
  sessionId: string;
  layerId: string;
  strokeId: string;
  tool: "brush" | "eraser";
  color: string;
  strokeWidth: number;
  delta: number[];
}

export interface StrokeEndMessage {
  type: "stroke:end";
  sessionId: string;
  strokeId: string;
}
