"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Check, Download, FileWarning, Loader2, RefreshCw } from "lucide-react";
import type { Job } from "../lib/types";
import { cancelJob } from "../lib/api";

interface Props {
  job: Job;
  onRefresh(): void;
}

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

const STAGE_SEGMENTS = [
  { status: "processing", label: "Prep", start: 0, end: 5 },
  { status: "transcribing", label: "Transcribe", start: 5, end: 80 },
  { status: "translating", label: "Translate", start: 80, end: 95 },
  { status: "exporting", label: "Export", start: 95, end: 100 },
] as const;

function statusAccent(status: Job["status"]) {
  switch (status) {
    case "completed":
      return "text-emerald-400";
    case "failed":
      return "text-red-400";
    case "cancelled":
      return "text-slate-400";
    default:
      return "text-brand";
  }
}

export function JobCard({ job, onRefresh }: Props) {
  const progress = Math.min(100, Math.round(job.progress.percent));

  const stageItems = STAGE_SEGMENTS.map((segment) => {
    const done = job.progress.percent >= segment.end - 0.5;
    const active = job.status === segment.status && !done;
    return {
      ...segment,
      state: done ? "done" : active ? "active" : "pending",
    } as const;
  });

  const created = useMemo(() => {
    const date = new Date(job.created_at);
    return date.toLocaleString();
  }, [job.created_at]);

  const handleCancel = async () => {
    await cancelJob(job.id);
    onRefresh();
  };

  return (
    <motion.div
      layout
      className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg"
      initial={{ opacity: 0, translateY: 16 }}
      animate={{ opacity: 1, translateY: 0 }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Job #{job.id.slice(0, 8)}</h3>
          <p className="text-xs text-slate-400">Created {created}</p>
        </div>
        <span className={`text-xs font-semibold uppercase tracking-wide ${statusAccent(job.status)}`}>
          {job.status}
        </span>
      </div>

      <div className="relative h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full bg-gradient-to-r from-brand to-purple-500 transition-all"
          style={{ width: `${progress}%` }}
        />
        <div className="pointer-events-none absolute inset-0 flex">
          {STAGE_SEGMENTS.map((segment, index) => (
            <div
              key={segment.status}
              style={{ width: `${segment.end - segment.start}%` }}
              className={`${index === 0 ? "" : "border-l"} border-slate-900/50`}
            />
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between text-sm text-slate-300">
        <span>{job.progress.message}</span>
        <span>{progress}%</span>
      </div>

      <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wide">
        {stageItems.map((stage) => {
          const base = "rounded-full px-3 py-1 border";
          if (stage.state === "done") {
            return (
              <span key={stage.status} className={`${base} border-emerald-500/40 bg-emerald-500/10 text-emerald-200 flex items-center gap-1`}>
                <Check className="h-3 w-3" /> {stage.label}
              </span>
            );
          }
          if (stage.state === "active") {
            return (
              <span key={stage.status} className={`${base} border-brand/40 bg-brand/10 text-brand flex items-center gap-1`}>
                <Loader2 className="h-3 w-3 animate-spin" /> {stage.label}
              </span>
            );
          }
          return (
            <span key={stage.status} className={`${base} border-slate-700 bg-slate-900 text-slate-400`}>
              {stage.label}
            </span>
          );
        })}
      </div>

      {job.error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/40 bg-red-900/30 px-3 py-2 text-xs text-red-200">
          <FileWarning className="h-4 w-4" />
          {job.error}
        </div>
      )}

      {job.summary && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-300">
          {job.summary}
        </div>
      )}

      {job.artifacts.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Artifacts</h4>
          <div className="flex flex-wrap gap-2">
            {job.artifacts.map((artifact) => {
              const filename = artifact.path.split("/").pop() ?? artifact.label;
              return (
                <a
                  key={`${job.id}-${filename}`}
                  href={`${apiBase}/jobs/${job.id}/artifacts/${encodeURIComponent(filename)}`}
                  className="flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200 transition hover:border-brand hover:text-white"
                >
                  <Download className="h-3 w-3" /> {artifact.label}
                </a>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-2 text-xs text-slate-400">
        <button
          type="button"
          onClick={onRefresh}
          className="flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200 transition hover:border-brand hover:text-white"
        >
          <RefreshCw className="h-3 w-3" /> Refresh
        </button>
        {!(job.status === "completed" || job.status === "failed" || job.status === "cancelled") && (
          <button
            type="button"
            onClick={handleCancel}
            className="flex items-center gap-2 rounded-full border border-red-500/40 px-3 py-1 text-xs text-red-300 transition hover:bg-red-500/20"
          >
            <Loader2 className="h-3 w-3" /> Cancel
          </button>
        )}
      </div>
    </motion.div>
  );
}
