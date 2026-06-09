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
      className="icon-btn-26"
      data-active={active ? "true" : undefined}
      data-danger={danger ? "true" : undefined}
    >
      {children}
    </button>
  );
}
