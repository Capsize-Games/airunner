import {
  Activity, Book, BotMessageSquare, Brain, ChevronUp, CircleCheck,
  CircleStop, CircleX, Cloud, Copy, Database, DatabaseZap, Dices,
  Grid2x2Check, History, Image, Images, Info, Layers, Loader,
  MessageSquareHeart, MessageSquareText, Mic, OctagonAlert,
  PanelRightOpen, Pencil, Play, Plus, Puzzle, RotateCcwSquare,
  ScanText, Settings, Settings2, SlidersHorizontal, Sparkles,
  Speaker, Trash, Upload,
  type LucideIcon,
} from "lucide-react";

/* ── Map SVG filenames (kebab-case) to lucide-react components ── */
const MAP: Record<string, LucideIcon> = {
  activity: Activity,
  book: Book,
  copy: Copy,
  "bot-message-square": BotMessageSquare,
  brain: Brain,
  "chevron-up": ChevronUp,
  "circle-check": CircleCheck,
  "circle-stop": CircleStop,
  "circle-x": CircleX,
  cloud: Cloud,
  database: Database,
  "database-zap": DatabaseZap,
  dices: Dices,
  "grid-2x2-check": Grid2x2Check,
  history: History,
  image: Image,
  images: Images,
  info: Info,
  layers: Layers,
  loader: Loader,
  "message-square-heart": MessageSquareHeart,
  "message-square-text": MessageSquareText,
  mic: Mic,
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
  trash: Trash,
  upload: Upload,
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
