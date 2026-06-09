// ── Top Bar ─────────────────────────────────────────────────────────────
// App header with logo and integrated action menu bar.
// ──────────────────────────────────────────────────────────────────────────
import ActionMenuBar from "./action-menu-bar";

export default function TopBar() {
  return (
    <div className="topbar">
      <div className="topbar-logo">
        AI <span>Runner</span>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <ActionMenuBar />
      </div>
    </div>
  );
}
