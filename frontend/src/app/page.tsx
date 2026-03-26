"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import {
  GitPullRequest,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  ArrowUpRight,
  FileCode2,
  Shield,
} from "lucide-react";

const priorityConfig: Record<string, { dot: string; badge: string; glow: string }> = {
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

const statusIcons: Record<string, any> = {
  pending: Clock,
  posted: CheckCircle2,
  error: AlertTriangle,
};

export default function FeedPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReviews = async () => {
      try {
        const result = await api.getReviews({ limit: 50 });
        setData(result);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load reviews");
      } finally {
        setLoading(false);
      }
    };

    fetchReviews();
    const interval = setInterval(fetchReviews, 30000);
    return () => clearInterval(interval);
  }, []);

  const reviews = data?.reviews || [];

  return (
    <div className="flex min-h-screen bg-[#080c14]">
      <Sidebar />

      <main className="flex-1 ml-[260px]">
        {/* Ambient background */}
        <div className="fixed inset-0 ml-[260px] pointer-events-none">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-amber-500/[0.03] rounded-full blur-[120px]" />
          <div className="absolute bottom-0 left-[20%] w-[400px] h-[400px] bg-blue-500/[0.02] rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 px-10 py-10 max-w-6xl">
          {/* Header */}
          <header className="mb-10 fade-in">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-[11px] font-medium text-amber-400/70 uppercase tracking-[0.2em] mb-2">Dashboard</p>
                <h1 className="text-3xl font-semibold text-white tracking-tight">
                  Review Feed
                </h1>
                <p className="text-sm text-slate-500 mt-1.5">
                  Real-time stream of analyzed pull requests
                </p>
              </div>
              {data && (
                <div className="flex items-center gap-6 fade-in delay-2">
                  <div className="text-right">
                    <p className="text-2xl font-semibold text-white tabular-nums">{data.total || 0}</p>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Total Reviews</p>
                  </div>
                </div>
              )}
            </div>
            <div className="mt-6 h-px bg-gradient-to-r from-amber-500/20 via-amber-500/5 to-transparent" />
          </header>

          {/* Loading */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-40">
              <div className="relative">
                <Loader2 className="h-8 w-8 animate-spin text-amber-400/50" />
                <div className="absolute inset-0 bg-amber-400/10 rounded-full blur-2xl scale-[3]" />
              </div>
              <p className="text-[13px] text-slate-500 mt-5">Loading reviews…</p>
            </div>
          )}

          {/* Error */}
          {error && !loading && (
            <div className="fade-in rounded-2xl border border-red-500/10 bg-red-500/[0.03] p-8 text-center">
              <AlertTriangle className="h-8 w-8 text-red-400/50 mx-auto mb-3" />
              <p className="text-sm text-red-300/80">Unable to connect to the backend</p>
              <p className="text-xs text-slate-500 mt-1">Make sure the API server is running on port 8000</p>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && reviews.length === 0 && (
            <div className="fade-in flex flex-col items-center justify-center py-32">
              <div className="relative mb-6">
                <div className="absolute inset-0 bg-amber-400/[0.06] rounded-full blur-3xl scale-[2.5]" />
                <div className="relative w-20 h-20 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
                  <GitPullRequest className="h-8 w-8 text-slate-500" strokeWidth={1.5} />
                </div>
              </div>
              <h3 className="text-lg font-medium text-slate-300 mb-1.5">No reviews yet</h3>
              <p className="text-sm text-slate-500 max-w-sm text-center leading-relaxed">
                Push a pull request to any connected repository and geekPR will analyze it automatically.
              </p>
              <div className="flex items-center gap-6 mt-8">
                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                  <FileCode2 className="h-3.5 w-3.5" />
                  <span>Complexity Analysis</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                  <Shield className="h-3.5 w-3.5" />
                  <span>Security Scan</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                  <ArrowUpRight className="h-3.5 w-3.5" />
                  <span>Auto-post to GitHub</span>
                </div>
              </div>
            </div>
          )}

          {/* Review cards */}
          {!loading && reviews.length > 0 && (
            <div className="space-y-3">
              {reviews.map((review: any, idx: number) => {
                const StatusIcon = statusIcons[review.status] || Clock;
                const priority = priorityConfig[review.priority] || priorityConfig.Low;
                return (
                  <div
                    key={review.id}
                    className="fade-in group"
                    style={{ animationDelay: `${idx * 40}ms` }}
                  >
                    <div className={`relative rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:bg-white/[0.04] hover:border-white/[0.1] hover:shadow-xl ${priority.glow}`}>
                      <div className="flex items-start gap-5">
                        {/* Priority indicator */}
                        <div className="pt-1.5">
                          <div className={`w-2 h-2 rounded-full ${priority.dot}`} />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2.5 mb-2">
                            <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                              {review.repo}
                            </span>
                            <span className="text-slate-700">·</span>
                            <span className="text-[11px] font-mono text-amber-500/80 font-medium">
                              #{review.pr_number}
                            </span>
                          </div>

                          <h3 className="text-[15px] font-medium text-slate-200 mb-1 truncate group-hover:text-white transition-colors">
                            {review.function_name || review.pr_title}
                          </h3>

                          <p className="text-[12px] text-slate-600 font-mono truncate">
                            {review.file_path}
                            {review.line_number && <span className="text-slate-700">:{review.line_number}</span>}
                          </p>
                        </div>

                        {/* Right side */}
                        <div className="flex items-center gap-4 shrink-0">
                          {/* CC Score */}
                          <div className="text-right mr-1">
                            <p className="text-xl font-semibold text-white tabular-nums">{review.complexity_score}</p>
                            <p className="text-[9px] text-slate-600 uppercase tracking-widest">Complexity</p>
                          </div>

                          {/* Priority badge */}
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wider ring-1 ${priority.badge}`}>
                            {review.priority}
                          </span>

                          {/* Status */}
                          <StatusIcon className="h-4 w-4 text-slate-600" strokeWidth={1.5} />
                        </div>
                      </div>
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
