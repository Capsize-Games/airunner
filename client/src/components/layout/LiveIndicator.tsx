// ── Live Indicator ──────────────────────────────────────────────────────
import { useState, useEffect } from "react";
import { isWsConnected } from "../../features/api/WsApiClient";

export default function LiveIndicator() {
  const [connected, setConnected] =
    useState(isWsConnected);
  useEffect(() => {
    let canceled = false;
    const id = setInterval(() => {
      if (!canceled) setConnected(isWsConnected());
    }, 1000);
    return () => {
      canceled = true;
      clearInterval(id);
    };
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
