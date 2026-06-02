const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

export default function TopBar() {
  return (
    <div className="topbar">
      <div className="topbar-logo">
        <img src={icon("brain")} alt="" />
        AI <span>Runner</span>
      </div>
    </div>
  );
}
