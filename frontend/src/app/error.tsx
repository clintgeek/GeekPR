"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Caught in error space:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#080c14] p-4 text-center">
      <div className="max-w-md w-full rounded-2xl border border-red-500/10 bg-red-500/[0.03] p-8 fade-in">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10 mb-6">
          <AlertTriangle className="h-8 w-8 text-red-500/70" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">Something went wrong</h2>
        <p className="text-sm text-slate-400 mb-8 leading-relaxed">
          {error.message || "An unexpected error occurred while loading this page."}
        </p>
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-xl bg-red-500/10 px-5 py-2.5 text-sm font-medium text-red-400 hover:bg-red-500/20 transition-colors"
        >
          <RotateCcw className="h-4 w-4" />
          Try again
        </button>
      </div>
    </div>
  );
}
