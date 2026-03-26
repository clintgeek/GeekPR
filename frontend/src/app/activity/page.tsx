"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import { CheckCircle2, XCircle, Clock, Cog, Loader2, Inbox } from "lucide-react";

const statusConfig: Record<string, { icon: any; color: string; dot: string; badge: string }> = {
  queued: { icon: Clock, color: "text-slate-400", dot: "bg-slate-400", badge: "bg-slate-500/10 text-slate-400 ring-slate-500/20" },
  processing: { icon: Cog, color: "text-amber-400", dot: "bg-amber-400", badge: "bg-amber-500/10 text-amber-400 ring-amber-500/20" },
  complete: { icon: CheckCircle2, color: "text-emerald-400", dot: "bg-emerald-400", badge: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20" },
  failed: { icon: XCircle, color: "text-red-400", dot: "bg-red-400", badge: "bg-red-500/10 text-red-400 ring-red-500/20" },
};

export default function ActivityPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const result = await api.getJobs();
        setData(result);
      } finally {
        setLoading(false);
      }
    };
    fetchJobs();
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  const jobs = data?.jobs || [];

  return (
    <div className="flex min-h-screen bg-[#080c14]">
      <Sidebar />

      <main className="flex-1 ml-[260px]">
        <div className="fixed inset-0 ml-[260px] pointer-events-none">
          <div className="absolute top-[10%] left-[30%] w-[400px] h-[400px] bg-emerald-500/[0.02] rounded-full blur-[120px]" />
        </div>

        <div className="relative z-10 px-10 py-10 max-w-6xl">
          <header className="mb-10 fade-in">
            <p className="text-[11px] font-medium text-amber-400/70 uppercase tracking-[0.2em] mb-2">System</p>
            <h1 className="text-3xl font-semibold text-white tracking-tight">Activity</h1>
            <p className="text-sm text-slate-500 mt-1.5">Audit trail of webhooks, jobs, and review actions</p>
            <div className="mt-6 h-px bg-gradient-to-r from-amber-500/20 via-amber-500/5 to-transparent" />
          </header>

          {loading && (
            <div className="flex flex-col items-center justify-center py-40">
              <Loader2 className="h-8 w-8 animate-spin text-amber-400/50" />
              <p className="text-[13px] text-slate-500 mt-5">Loading activity…</p>
            </div>
          )}

          {!loading && jobs.length === 0 && (
            <div className="fade-in flex flex-col items-center justify-center py-32">
              <div className="relative mb-6">
                <div className="absolute inset-0 bg-amber-400/[0.06] rounded-full blur-3xl scale-[2.5]" />
                <div className="relative w-20 h-20 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
                  <Inbox className="h-8 w-8 text-slate-500" strokeWidth={1.5} />
                </div>
              </div>
              <h3 className="text-lg font-medium text-slate-300 mb-1.5">No activity yet</h3>
              <p className="text-sm text-slate-500 max-w-sm text-center leading-relaxed">
                Webhook events and job executions will appear here in real-time.
              </p>
            </div>
          )}

          {!loading && jobs.length > 0 && (
            <div className="space-y-2">
              {jobs.map((job: any, idx: number) => {
                const config = statusConfig[job.status] || statusConfig.queued;
                const Icon = config.icon;
                return (
                  <div
                    key={job.id}
                    className="fade-in group"
                    style={{ animationDelay: `${idx * 30}ms` }}
                  >
                    <div className="flex items-center gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] px-5 py-4 transition-all duration-200 hover:bg-white/[0.04] hover:border-white/[0.1]">
                      <Icon className={`h-4 w-4 ${config.color} shrink-0`} strokeWidth={1.8} />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2.5">
                          <span className="text-[13px] font-medium text-slate-200">{job.repo}</span>
                          <span className="text-slate-700">·</span>
                          <span className="text-[12px] font-mono text-amber-500/70">#{job.pr_number}</span>
                        </div>
                        {job.error_message && (
                          <p className="text-[11px] text-red-400/70 mt-0.5 truncate">{job.error_message}</p>
                        )}
                      </div>

                      <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wider ring-1 ${config.badge}`}>
                        {job.status}
                      </span>

                      <span className="text-[11px] text-slate-600 tabular-nums whitespace-nowrap">
                        {job.created_at ? new Date(job.created_at).toLocaleString() : "—"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
