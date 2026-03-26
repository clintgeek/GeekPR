import { CheckCircle2, Clock, AlertTriangle, LucideIcon } from "lucide-react";

export interface PriorityConfigItem {
  dot: string;
  badge: string;
  glow: string;
}

export const priorityConfig: Record<string, PriorityConfigItem> = {
  High: {
    dot: "bg-red-400",
    badge: "bg-red-500/10 text-red-400 ring-red-500/20",
    glow: "shadow-red-500/5",
  },
  Medium: {
    dot: "bg-amber-400",
    badge: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
    glow: "shadow-amber-500/5",
  },
  Low: {
    dot: "bg-emerald-400",
    badge: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
    glow: "shadow-emerald-500/5",
  },
};

export const statusIcons: Record<string, LucideIcon> = {
  pending: Clock,
  posted: CheckCircle2,
  error: AlertTriangle,
};
