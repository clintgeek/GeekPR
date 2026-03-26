"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import { ChevronRight, Check } from "lucide-react";

export default function SettingsPage() {
  const [repoInput, setRepoInput] = useState("");
  const [config, setConfig] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function loadConfig() {
    const parts = repoInput.split("/");
    if (parts.length !== 2) return;
    try {
      const { api } = await import("@/lib/api");
      const data = await api.getRepoConfig(parts[0], parts[1]);
      setConfig(data);
      setMessage("");
    } catch {
      setMessage("Failed to load config");
    }
  }

  async function saveConfig() {
    const parts = repoInput.split("/");
    if (parts.length !== 2 || !config) return;
    setSaving(true);
    try {
      const { api } = await import("@/lib/api");
      await api.updateRepoConfig(parts[0], parts[1], config);
      setMessage("Saved");
      setTimeout(() => setMessage(""), 3000);
    } catch {
      setMessage("Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const inputClass =
    "w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-[13px] text-slate-200 font-mono placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-amber-500/30 focus:border-amber-500/20 transition-all";

  return (
    <div className="flex min-h-screen bg-[#080c14]">
      <Sidebar />

      <main className="flex-1 ml-[260px]">
        <div className="fixed inset-0 ml-[260px] pointer-events-none">
          <div className="absolute bottom-[-200px] right-[-100px] w-[500px] h-[500px] bg-amber-500/[0.02] rounded-full blur-[120px]" />
        </div>

        <div className="relative z-10 px-10 py-10 max-w-3xl">
          <header className="mb-10 fade-in">
            <p className="text-[11px] font-medium text-amber-400/70 uppercase tracking-[0.2em] mb-2">Configuration</p>
            <h1 className="text-3xl font-semibold text-white tracking-tight">Settings</h1>
            <p className="text-sm text-slate-500 mt-1.5">Configure analysis rules per repository</p>
            <div className="mt-6 h-px bg-gradient-to-r from-amber-500/20 via-amber-500/5 to-transparent" />
          </header>

          {/* Repo selector */}
          <div className="mb-8 fade-in delay-1">
            <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2.5">Repository</label>
            <div className="flex gap-3">
              <input
                type="text"
                value={repoInput}
                onChange={(e) => setRepoInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadConfig()}
                placeholder="owner/repo"
                className={inputClass + " flex-1"}
              />
              <button
                onClick={loadConfig}
                className="px-5 py-3 rounded-xl bg-amber-500 text-[#080c14] text-[13px] font-semibold hover:bg-amber-400 transition-colors flex items-center gap-2 shrink-0"
              >
                Load
                <ChevronRight className="h-3.5 w-3.5" strokeWidth={2.5} />
              </button>
            </div>
          </div>

          {/* Config panel */}
          {config && (
            <div className="space-y-4 fade-in">
              {/* Complexity threshold */}
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6">
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <p className="text-[13px] font-medium text-slate-200">Complexity Threshold</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Functions above this CC score get flagged</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-semibold text-white tabular-nums">{config.cc_threshold}</p>
                    <p className="text-[9px] text-slate-600 uppercase tracking-widest">CC Score</p>
                  </div>
                </div>
                <input
                  type="range"
                  min={1}
                  max={30}
                  value={config.cc_threshold}
                  onChange={(e) => setConfig({ ...config, cc_threshold: +e.target.value })}
                  className="w-full h-1 bg-white/[0.06] rounded-full appearance-none cursor-pointer accent-amber-400"
                />
              </div>

              {/* Toggle: Bandit */}
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[13px] font-medium text-slate-200">Security Scan</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Bandit analysis for secrets, eval(), injections</p>
                  </div>
                  <button
                    onClick={() => setConfig({ ...config, bandit_enabled: !config.bandit_enabled })}
                    className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${config.bandit_enabled ? "bg-amber-500" : "bg-white/[0.08]"}`}
                  >
                    <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${config.bandit_enabled ? "translate-x-[22px]" : "translate-x-0.5"}`} />
                  </button>
                </div>
              </div>

              {/* Toggle: Auto-post */}
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[13px] font-medium text-slate-200">Auto-Post Reviews</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Post suggestions to GitHub automatically</p>
                  </div>
                  <button
                    onClick={() => setConfig({ ...config, auto_post: !config.auto_post })}
                    className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${config.auto_post ? "bg-amber-500" : "bg-white/[0.08]"}`}
                  >
                    <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${config.auto_post ? "translate-x-[22px]" : "translate-x-0.5"}`} />
                  </button>
                </div>
              </div>

              {/* LLM Provider */}
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6">
                <p className="text-[13px] font-medium text-slate-200 mb-4">LLM Provider</p>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {[
                    { key: "ollama", label: "Ollama", desc: "Local inference" },
                    { key: "openai", label: "OpenAI", desc: "Cloud API" },
                  ].map((p) => (
                    <button
                      key={p.key}
                      onClick={() => setConfig({
                        ...config,
                        llm_provider: p.key,
                        llm_model: p.key === "openai" ? "gpt-4o" : "codellama",
                      })}
                      className={`relative px-4 py-3 rounded-xl text-left transition-all duration-200 border ${
                        config.llm_provider === p.key
                          ? "border-amber-500/30 bg-amber-500/[0.06]"
                          : "border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]"
                      }`}
                    >
                      <p className={`text-[13px] font-medium ${config.llm_provider === p.key ? "text-amber-400" : "text-slate-300"}`}>{p.label}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">{p.desc}</p>
                      {config.llm_provider === p.key && (
                        <div className="absolute top-3 right-3 w-4 h-4 rounded-full bg-amber-500 flex items-center justify-center">
                          <Check className="h-2.5 w-2.5 text-[#080c14]" strokeWidth={3} />
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* LLM Model */}
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6">
                <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2.5">Model</label>
                <input
                  type="text"
                  value={config.llm_model}
                  onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
                  className={inputClass}
                />
                <p className="text-[10px] text-slate-600 mt-2">
                  {config.llm_provider === "openai" ? "gpt-4o · gpt-4o-mini · gpt-3.5-turbo" : "codellama · deepseek-coder · llama3"}
                </p>
              </div>

              {/* Exclude patterns */}
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6">
                <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2.5">Exclude Patterns</label>
                <input
                  type="text"
                  value={config.exclude_patterns}
                  onChange={(e) => setConfig({ ...config, exclude_patterns: e.target.value })}
                  placeholder="**/migrations/**, **/tests/**"
                  className={inputClass}
                />
                <p className="text-[10px] text-slate-600 mt-2">Comma-separated globs. Matching files are skipped.</p>
              </div>

              {/* Save */}
              <div className="flex items-center gap-4 pt-2">
                <button
                  onClick={saveConfig}
                  disabled={saving}
                  className="px-6 py-3 rounded-xl bg-amber-500 text-[#080c14] text-[13px] font-semibold hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {saving ? "Saving…" : "Save Configuration"}
                </button>
                {message && (
                  <span className={`text-[12px] font-medium ${message.startsWith("Failed") ? "text-red-400" : "text-emerald-400"}`}>
                    {message}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
