"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import { BarChart3, TrendingDown, AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReviews = async () => {
      try {
        const result = await api.getReviews({ limit: 100 });
        setData(result);
      } finally {
        setLoading(false);
      }
    };
    fetchReviews();
  }, []);

  const reviews = data?.reviews || [];
  const totalReviews = reviews.length;
  const avgComplexity =
    reviews.length > 0
      ? (reviews.reduce((sum: number, r: any) => sum + r.complexity_score, 0) / reviews.length).toFixed(1)
      : "—";
  const highPriority = reviews.filter((r: any) => r.priority === "High").length;
  const posted = reviews.filter((r: any) => r.status === "posted").length;

  const stats = [
    { label: "Total Reviews", value: totalReviews, icon: BarChart3, color: "text-blue-400", bg: "bg-blue-500/10" },
    { label: "Avg Complexity", value: avgComplexity, icon: TrendingDown, color: "text-emerald-400", bg: "bg-emerald-500/10" },
    { label: "High Priority", value: highPriority, icon: AlertTriangle, color: "text-red-400", bg: "bg-red-500/10" },
    { label: "Posted", value: posted, icon: CheckCircle2, color: "text-amber-400", bg: "bg-amber-500/10" },
  ];

  return (
    <div className="flex min-h-screen bg-[#080c14]">
      <Sidebar />

      <main className="flex-1 ml-[260px]">
        <div className="fixed inset-0 ml-[260px] pointer-events-none">
          <div className="absolute top-[-200px] right-[-100px] w-[500px] h-[500px] bg-blue-500/[0.03] rounded-full blur-[120px]" />
        </div>

        <div className="relative z-10 px-10 py-10 max-w-6xl">
          <header className="mb-10 fade-in">
            <p className="text-[11px] font-medium text-amber-400/70 uppercase tracking-[0.2em] mb-2">Insights</p>
            <h1 className="text-3xl font-semibold text-white tracking-tight">Analytics</h1>
            <p className="text-sm text-slate-500 mt-1.5">Code quality trends and review metrics</p>
            <div className="mt-6 h-px bg-gradient-to-r from-amber-500/20 via-amber-500/5 to-transparent" />
          </header>

          {loading && (
            <div className="flex flex-col items-center justify-center py-40">
              <Loader2 className="h-8 w-8 animate-spin text-amber-400/50" />
              <p className="text-[13px] text-slate-500 mt-5">Loading analytics…</p>
            </div>
          )}

          {!loading && (
            <>
              {/* Stat cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
                {stats.map((stat, idx) => {
                  const Icon = stat.icon;
                  return (
                    <div
                      key={stat.label}
                      className="fade-in group"
                      style={{ animationDelay: `${idx * 60}ms` }}
                    >
                      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:bg-white/[0.04] hover:border-white/[0.1]">
                        <div className="flex items-center justify-between mb-4">
                          <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">{stat.label}</p>
                          <div className={`w-8 h-8 rounded-lg ${stat.bg} flex items-center justify-center`}>
                            <Icon className={`h-4 w-4 ${stat.color}`} strokeWidth={1.8} />
                          </div>
                        </div>
                        <p className="text-3xl font-semibold text-white tabular-nums">{stat.value}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Priority breakdown */}
              <div className="fade-in delay-4">
                <h2 className="text-[13px] font-medium text-slate-400 uppercase tracking-wider mb-4">Priority Breakdown</h2>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: "High", count: reviews.filter((r: any) => r.priority === "High").length, color: "bg-red-400", total: totalReviews },
                    { label: "Medium", count: reviews.filter((r: any) => r.priority === "Medium").length, color: "bg-amber-400", total: totalReviews },
                    { label: "Low", count: reviews.filter((r: any) => r.priority === "Low").length, color: "bg-emerald-400", total: totalReviews },
                  ].map((item) => {
                    const pct = item.total > 0 ? Math.round((item.count / item.total) * 100) : 0;
                    return (
                      <div key={item.label} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${item.color}`} />
                            <span className="text-[13px] text-slate-300 font-medium">{item.label}</span>
                          </div>
                          <span className="text-[13px] text-slate-500 tabular-nums">{item.count}</span>
                        </div>
                        <div className="w-full h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.color} rounded-full transition-all duration-700`}
                            style={{ width: `${pct}%`, opacity: 0.6 }}
                          />
                        </div>
                        <p className="text-[10px] text-slate-600 mt-2 tabular-nums">{pct}%</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
