// ── Live Indicator ──────────────────────────────────────────────────────
import { useState, useEffect } from "react";
import {
  isWsConnected,
  onWsConnectionChange,
} from "../../features/api/WsApiClient";

export default function LiveIndicator() {
  const [connected, setConnected] =
    useState(isWsConnected);
  useEffect(() => {
    // Sync once in case the state changed between render and effect, then
    // update on pushed connect/disconnect transitions (no polling).
    setConnected(isWsConnected());
    return onWsConnectionChange(setConnected);
  }, []);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 11,
        fontFamily: "monospace",
        color: connected
          ? "rgba(0,200,100,0.7)"
          : "rgba(255,150,50,0.6)",
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: connected
            ? "rgb(0,200,100)"
            : "rgb(255,150,50)",
          display: "inline-block",
        }}
      />
      {connected ? "Live" : "Reconnecting…"}
    </span>
  );
}
