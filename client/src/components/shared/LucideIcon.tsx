import {
  Activity, Book, BotMessageSquare, Brain,
  ChevronDown, ChevronLeft, ChevronRight, ChevronUp,
  CircleCheck, CircleStop, CircleX, Cloud, Copy, Database, DatabaseZap, Dices,
  Drama, Eraser, FolderOpen, Globe, Save, Grid2x2Check, History, Image, Images, Info, Layers, LayersPlus, Loader,
  MessageSquareHeart, MessageSquareText, Mic, Move, OctagonAlert,
  PanelRightOpen, Pencil, Play, Plus, Puzzle, RotateCcwSquare,
  ScanText, Settings, Settings2, SlidersHorizontal, Sparkles,
  Speaker, SquareDashed, Trash, Upload, User,
  type LucideIcon,
} from "lucide-react";

/* ── Map SVG filenames (kebab-case) to lucide-react components ── */
const MAP: Record<string, LucideIcon> = {
  activity: Activity,
  book: Book,
  copy: Copy,
  "bot-message-square": BotMessageSquare,
  brain: Brain,
  "chevron-down": ChevronDown,
  "chevron-left": ChevronLeft,
  "chevron-right": ChevronRight,
  "chevron-up": ChevronUp,
  "circle-check": CircleCheck,
  "circle-stop": CircleStop,
  "circle-x": CircleX,
  cloud: Cloud,
  database: Database,
  "database-zap": DatabaseZap,
  dices: Dices,
  drama: Drama,
  eraser: Eraser,
  "folder-open": FolderOpen,
  save: Save,
  globe: Globe,
  "grid-2x2-check": Grid2x2Check,
  history: History,
  image: Image,
  images: Images,
  info: Info,
  layers: Layers,
  "layers-plus": LayersPlus,
  loader: Loader,
  "message-square-heart": MessageSquareHeart,
  "message-square-text": MessageSquareText,
  mic: Mic,
  move: Move,
  "octagon-alert": OctagonAlert,
  "panel-right-open": PanelRightOpen,
  pencil: Pencil,
  play: Play,
  plus: Plus,
  puzzle: Puzzle,
  "rotate-ccw-square": RotateCcwSquare,
  "scan-text": ScanText,
  settings: Settings,
  "settings-2": Settings2,
  "sliders-horizontal": SlidersHorizontal,
  sparkles: Sparkles,
  speaker: Speaker,
  "square-dashed": SquareDashed,
  trash: Trash,
  upload: Upload,
  user: User,
};

interface Props {
  name: string;
  size?: number;
  className?: string;
}

export default function LucideIcon({ name, size = 20, className }: Props) {
  const Icon = MAP[name];
  if (!Icon) {
    console.warn(`LucideIcon: unknown icon "${name}"`);
    return null;
  }
  return <Icon size={size} className={`lucide-icon ${className ?? ""}`.trim()} />;
}
