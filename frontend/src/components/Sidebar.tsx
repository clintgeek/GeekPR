"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  Zap,
  LayoutDashboard,
  BarChart3,
  Activity,
  Settings,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Feed", icon: LayoutDashboard },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-[260px] flex flex-col border-r border-white/[0.06] bg-[#0a0f1a]/80 backdrop-blur-xl">
      {/* Brand */}
      <div className="flex items-center gap-3 px-7 pt-8 pb-7">
        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 shadow-lg shadow-amber-500/20">
          <Zap className="h-4.5 w-4.5 text-slate-900" strokeWidth={2.5} />
        </div>
        <div>
          <h1 className="text-[15px] font-semibold tracking-tight text-white">geekPR</h1>
          <p className="text-[10px] text-slate-500 font-medium tracking-wide uppercase">Autonomous Review</p>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-5 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />

      {/* Navigation */}
      <nav className="flex-1 px-4 py-5 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                group flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-200
                ${isActive
                  ? "bg-white/[0.07] text-white shadow-sm shadow-black/10"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                }
              `}
            >
              <Icon
                className={`h-4 w-4 transition-colors ${isActive ? "text-amber-400" : "text-slate-500 group-hover:text-slate-400"}`}
                strokeWidth={1.8}
              />
              {item.label}
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-amber-400 shadow-sm shadow-amber-400/50" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-7 py-5 border-t border-white/[0.04]">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-glow" />
          <span className="text-[11px] text-slate-500 font-medium">System Online</span>
        </div>
        <p className="text-[10px] text-slate-600 mt-1.5">v0.1.0</p>
      </div>
    </aside>
  );
}
