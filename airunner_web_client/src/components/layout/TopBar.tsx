import LucideIcon from "../shared/LucideIcon";

export default function TopBar() {
  return (
    <div className="topbar">
      <div className="topbar-logo">
        <LucideIcon name="brain" />
        AI <span>Runner</span>
      </div>
    </div>
  );
}
