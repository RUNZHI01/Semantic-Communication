/**
 * Icon Library - Centralized icon exports using lucide-react
 *
 * Usage:
 * import { Icon } from '@/components/icons'
 * <Icon name="activity" size={20} className="text-accent" />
 */

import * as LucideIcons from 'lucide-react';
import { createElement } from 'react';

export type IconName = keyof typeof LucideIcons;

export interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  color?: string;
  strokeWidth?: number;
}

/**
 * Generic Icon component that dynamically renders any lucide-react icon
 */
export function Icon({ name, size = 20, className, color, strokeWidth = 2 }: IconProps) {
  const IconComponent = LucideIcons[name] as React.ComponentType<{ size?: number; className?: string; color?: string; strokeWidth?: number }>;

  if (!IconComponent) {
    console.warn(`Icon "${name}" not found in lucide-react`);
    return null;
  }

  return createElement(IconComponent, {
    size,
    className,
    color,
    strokeWidth,
  });
}

/**
 * Commonly used icons - direct exports for convenience
 */
export const Icons = {
  // Navigation & Actions
  ArrowRight: LucideIcons.ArrowRight,
  ArrowLeft: LucideIcons.ArrowLeft,
  ArrowUp: LucideIcons.ArrowUp,
  ArrowDown: LucideIcons.ArrowDown,
  ChevronRight: LucideIcons.ChevronRight,
  ChevronLeft: LucideIcons.ChevronLeft,
  Home: LucideIcons.Home,
  Settings: LucideIcons.Settings,
  Menu: LucideIcons.Menu,
  X: LucideIcons.X,

  // Status & Indicators
  Check: LucideIcons.Check,
  CheckCircle: LucideIcons.CheckCircle,
  XCircle: LucideIcons.XCircle,
  AlertTriangle: LucideIcons.AlertTriangle,
  AlertCircle: LucideIcons.AlertCircle,
  Info: LucideIcons.Info,
  Zap: LucideIcons.Zap,
  Activity: LucideIcons.Activity,

  // Data & Charts
  BarChart: LucideIcons.BarChart,
  LineChart: LucideIcons.LineChart,
  PieChart: LucideIcons.PieChart,
  TrendingUp: LucideIcons.TrendingUp,
  TrendingDown: LucideIcons.TrendingDown,
  Database: LucideIcons.Database,

  // System & Hardware
  Cpu: LucideIcons.Cpu,
  MemoryStick: LucideIcons.MemoryStick,
  HardDrive: LucideIcons.HardDrive,
  Wifi: LucideIcons.Wifi,
  WifiOff: LucideIcons.WifiOff,
  Radio: LucideIcons.Radio,
  Server: LucideIcons.Server,
  Network: LucideIcons.Network,

  // Maps & Location
  Map: LucideIcons.Map,
  Globe: LucideIcons.Globe,
  Navigation: LucideIcons.Navigation,
  Compass: LucideIcons.Compass,
  Crosshair: LucideIcons.Crosshair,
  Radar: LucideIcons.Radar,

  // Time & Scheduling
  Clock: LucideIcons.Clock,
  Timer: LucideIcons.Timer,
  Calendar: LucideIcons.Calendar,
  Hourglass: LucideIcons.Hourglass,

  // Controls
  Play: LucideIcons.Play,
  Pause: LucideIcons.Pause,
  Square: LucideIcons.Square,
  RotateCcw: LucideIcons.RotateCcw,
  RefreshCw: LucideIcons.RefreshCw,
  Power: LucideIcons.Power,
  ToggleLeft: LucideIcons.ToggleLeft,
  ToggleRight: LucideIcons.ToggleRight,

  // Files & Documents
  File: LucideIcons.File,
  FileText: LucideIcons.FileText,
  Folder: LucideIcons.Folder,
  Download: LucideIcons.Download,
  Upload: LucideIcons.Upload,

  // Communication
  MessageSquare: LucideIcons.MessageSquare,
  Send: LucideIcons.Send,
  Bell: LucideIcons.Bell,
  Mail: LucideIcons.Mail,

  // Users & Security
  User: LucideIcons.User,
  Users: LucideIcons.Users,
  Shield: LucideIcons.Shield,
  Lock: LucideIcons.Lock,
  Unlock: LucideIcons.Unlock,
  Key: LucideIcons.Key,

  // Media
  Image: LucideIcons.Image,
  Video: LucideIcons.Video,
  Mic: LucideIcons.Mic,
  Volume2: LucideIcons.Volume2,
  VolumeX: LucideIcons.VolumeX,

  // Tools
  Wrench: LucideIcons.Wrench,
  Hammer: LucideIcons.Hammer,
  Scan: LucideIcons.Scan,
  Search: LucideIcons.Search,
  Filter: LucideIcons.Filter,

  // Misc
  MoreHorizontal: LucideIcons.MoreHorizontal,
  MoreVertical: LucideIcons.MoreVertical,
  ExternalLink: LucideIcons.ExternalLink,
  Link: LucideIcons.Link,
  Unlink: LucideIcons.Unlink,
  Copy: LucideIcons.Copy,
  Trash: LucideIcons.Trash,
  Edit: LucideIcons.Edit,
  Plus: LucideIcons.Plus,
  Minus: LucideIcons.Minus,
  Eye: LucideIcons.Eye,
  EyeOff: LucideIcons.EyeOff,
  Heart: LucideIcons.Heart,
  Star: LucideIcons.Star,
  Moon: LucideIcons.Moon,
  Sun: LucideIcons.Sun,
  Maximize: LucideIcons.Maximize,
  Minimize: LucideIcons.Minimize,
};

export default Icons;
