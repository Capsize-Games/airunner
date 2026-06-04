/**
 * Simple icon button used in the layers sidebar.
 *
 * Note: there is a separate IconBtn component in ToolBarTools.tsx with
 * different styling (supports an "active" state). Do not conflate the two.
 */

interface IconBtnProps {
  title: string;
  disabled?: boolean;
  danger?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}

export default function IconBtn({
  title,
  disabled,
  danger,
  onClick,
  children,
}: IconBtnProps) {
  return (
    <button
      title={title}
      disabled={disabled}
      onClick={onClick}
      style={{
        width: 22, height: 22, padding: 0, flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        border: "none", borderRadius: 4, background: "transparent",
        color: disabled ? "rgba(255,255,255,0.15)"
          : danger ? "rgba(255,100,100,0.65)"
          : "rgba(255,255,255,0.5)",
        cursor: disabled ? "default" : "pointer",
      }}
    >
      {children}
    </button>
  );
}
