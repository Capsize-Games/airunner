interface IconBtnProps {
  title: string;
  disabled?: boolean;
  danger?: boolean;
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}

export default function IconBtn({
  title,
  disabled,
  danger,
  active,
  onClick,
  children,
}: IconBtnProps) {
  return (
    <button
      title={title}
      disabled={disabled}
      onClick={onClick}
      style={{
        width: 26, height: 26, padding: 0, flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        border: "none", borderRadius: 4,
        background: active ? "rgba(99,153,255,0.18)" : "transparent",
        color: disabled ? "rgba(var(--theme-text-rgb), 0.15)"
          : danger ? "rgba(255,100,100,0.65)"
          : active ? "#6fa8ff"
          : "rgba(var(--theme-text-rgb), 0.5)",
        cursor: disabled ? "default" : "pointer",
        boxShadow: active ? "inset 0 0 0 1px rgba(99,153,255,0.4)" : "none",
      }}
    >
      {children}
    </button>
  );
}
