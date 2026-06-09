// ── Action Menu Bar Styles ──────────────────────────────────────────────
import type { CSSProperties } from "react";

export const barStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  height: 26,
  flexShrink: 0,
  padding: "0 2px",
  gap: 0,
  zIndex: 200,
  userSelect: "none",
};

export const menuBtnStyle: CSSProperties = {
  background: "none",
  border: "none",
  color: "rgba(255,255,255,0.65)",
  fontSize: 12,
  padding: "3px 10px",
  cursor: "pointer",
  fontFamily: "inherit",
  lineHeight: 1.4,
  whiteSpace: "nowrap",
};

export const menuBtnActiveStyle: CSSProperties = {
  ...menuBtnStyle,
  background: "rgba(99,153,255,0.18)",
  color: "#c8d8ff",
};

export const dropdownStyle: CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  minWidth: 180,
  background: "#1c1c2e",
  border: "1px solid rgba(255,255,255,0.12)",
  padding: "4px 0",
  boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
  zIndex: 300,
};

export const menuItemStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  width: "100%",
  padding: "5px 14px",
  background: "none",
  border: "none",
  color: "rgba(255,255,255,0.75)",
  fontSize: 12,
  cursor: "pointer",
  fontFamily: "inherit",
  textAlign: "left",
  lineHeight: 1.5,
  gap: 20,
};

export const checkboxItemStyle: CSSProperties = {
  ...menuItemStyle,
  gap: 8,
};

export const submenuArrow: CSSProperties = {
  color: "rgba(255,255,255,0.35)",
  fontSize: 10,
  marginLeft: "auto",
};

export const submenuWrapperStyle: CSSProperties = {
  position: "absolute",
  top: -4,
  left: "100%",
  minWidth: 160,
  background: "#1c1c2e",
  border: "1px solid rgba(255,255,255,0.12)",
  padding: "4px 0",
  boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
  zIndex: 301,
};

export const checkMarkStyle: CSSProperties = {
  width: 14,
  textAlign: "center",
  color: "#6fa8ff",
  fontSize: 11,
};

export const dividerStyle: CSSProperties = {
  height: 1,
  background: "rgba(255,255,255,0.08)",
  margin: "3px 8px",
};
