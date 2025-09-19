"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Check, Download, FileWarning, Loader2, RefreshCw } from "lucide-react";
import type { Job } from "../lib/types";
import { cancelJob, triggerTranslation } from "../lib/api";

interface Props {
  job: Job;
  onRefresh(): void;
}

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

const LANG_CHOICES = [
  { value: "en", label: "English" },
  { value: "tr", label: "Turkish" },
  { value: "fa", label: "Persian" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "it", label: "Italian" },
];

const TRANSLATION_MODELS = [
  { value: "gpt-5-nano", label: "gpt-5-nano" },
  { value: "gpt-5-mini", label: "gpt-5-mini" },
];

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

  const translationRunning = job.status === "translating";
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(job.options.translation_languages ?? []);
  const [selectedModel, setSelectedModel] = useState(
    job.options.translation_model && job.options.translation_model !== "none"
      ? job.options.translation_model
      : "gpt-5-nano"
  );
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [submittingTranslation, setSubmittingTranslation] = useState(false);

  useEffect(() => {
    if (job.options.translation_languages?.length) {
      setSelectedLanguages(job.options.translation_languages);
    }
    if (job.options.translation_model && job.options.translation_model !== "none") {
      setSelectedModel(job.options.translation_model);
    }
  }, [job.options.translation_languages, job.options.translation_model]);

  const availableLanguages = useMemo(() => {
    const base = [...LANG_CHOICES];
    for (const lang of job.options.translation_languages ?? []) {
      if (!base.some((item) => item.value === lang)) {
        base.push({ value: lang, label: lang.toUpperCase() });
      }
    }
    return base;
  }, [job.options.translation_languages]);

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

  const toggleLanguage = (value: string) => {
    setSelectedLanguages((prev) =>
      prev.includes(value) ? prev.filter((lang) => lang !== value) : [...prev, value]
    );
  };

  const handleTranslate = async () => {
    if (!selectedLanguages.length) {
      setTranslationError("Select at least one language");
      return;
    }
    setTranslationError(null);
    setSubmittingTranslation(true);
    try {
      await triggerTranslation(job.id, {
        languages: selectedLanguages,
        model: selectedModel,
      });
      onRefresh();
    } catch (err: any) {
      setTranslationError(err?.message ?? "Failed to trigger translation");
    } finally {
      setSubmittingTranslation(false);
    }
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

      {job.status === "completed" || translationRunning ? (
        <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Translate captions</h4>
              <p className="text-[11px] text-slate-500">
                Generate new subtitle files in additional languages on demand.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {availableLanguages.map((lang) => (
              <button
                key={lang.value}
                type="button"
                onClick={() => toggleLanguage(lang.value)}
                className={`rounded-full px-3 py-1 text-xs transition ${
                  selectedLanguages.includes(lang.value)
                    ? "bg-brand text-white"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
                disabled={translationRunning}
              >
                {lang.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {TRANSLATION_MODELS.map((model) => (
              <button
                key={model.value}
                type="button"
                onClick={() => setSelectedModel(model.value)}
                className={`rounded-full px-3 py-1 text-xs transition ${
                  selectedModel === model.value
                    ? "bg-brand text-white"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
                disabled={translationRunning}
              >
                {model.label}
              </button>
            ))}
          </div>
          {translationError && (
            <div className="rounded-lg border border-red-500/30 bg-red-900/20 px-3 py-2 text-xs text-red-200">
              {translationError}
            </div>
          )}
          <button
            type="button"
            onClick={handleTranslate}
            disabled={translationRunning || submittingTranslation}
            className="flex items-center justify-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs text-slate-200 transition hover:border-brand hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {(translationRunning || submittingTranslation) ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                Translating...
              </>
            ) : (
              "Generate translations"
            )}
          </button>
        </div>
      ) : null}

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
