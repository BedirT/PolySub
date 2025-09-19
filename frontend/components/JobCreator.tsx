"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Loader2, UploadCloud } from "lucide-react";
import useSWR from "swr";
import { createJob, fetchSystemSpecs } from "../lib/api";
import type { Job, JobOptions, SystemSpecs } from "../lib/types";

const ENGINES = [
  { value: "faster-whisper", label: "Faster Whisper (Local)" },
  { value: "whisperx", label: "WhisperX Align + Diarization" },
  { value: "lightning-whisper-mlx", label: "Lightning Whisper (MLX)" },
  { value: "mlx-whisper", label: "MLX Whisper (Turbo)" },
  { value: "gpt-4o-transcribe", label: "OpenAI gpt-4o-transcribe" },
  { value: "gpt-4o-mini-transcribe", label: "OpenAI gpt-4o-mini-transcribe" },
  { value: "assemblyai", label: "AssemblyAI" },
  { value: "speech-recognition", label: "SpeechRecognition (Legacy)" },
];
interface Props {
  onJobCreated(job: Job): void;
}

export function JobCreator({ onJobCreated }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [engine, setEngine] = useState("faster-whisper");
  const [model, setModel] = useState("large-v3");
  const [alignment, setAlignment] = useState(true);
  const [diarization, setDiarization] = useState(false);
  const [formats, setFormats] = useState<string[]>(["srt", "vtt"]);
  const [device, setDevice] = useState<string>("auto");
  const [batchSize, setBatchSize] = useState<number | null>(null);
  const [quantization, setQuantization] = useState<string | null>(null);
  const [subtitleLeadIn, setSubtitleLeadIn] = useState<number | null>(null);
  const [subtitleLinger, setSubtitleLinger] = useState<number | null>(null);
  const [subtitleMinGap, setSubtitleMinGap] = useState<number | null>(null);
  const [subtitleMinDuration, setSubtitleMinDuration] = useState<number | null>(null);
  const [subtitleMaxChars, setSubtitleMaxChars] = useState<number | null>(null);
  const [subtitleMaxLines, setSubtitleMaxLines] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useCustomKeys, setUseCustomKeys] = useState(false);
  const [openaiKey, setOpenaiKey] = useState("");
  const [assemblyKey, setAssemblyKey] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const { data: systemSpecs } = useSWR<SystemSpecs>("system-specs", fetchSystemSpecs, {
    revalidateOnFocus: false,
  });

  const engineMeta = useMemo(() => systemSpecs?.engines?.[engine], [systemSpecs, engine]);
  const subtitleDefaults = systemSpecs?.subtitle_defaults;

  const engineOptions = useMemo(() => {
    return ENGINES.map((option) => {
      const meta = systemSpecs?.engines?.[option.value];
      const hasDevice = meta?.device_options?.some((d) => d.available) ?? true;
      const available = meta?.available === false ? false : hasDevice;
      return { ...option, disabled: !available };
    });
  }, [systemSpecs]);

  const modelChoices = engineMeta?.model_options?.choices ?? [];
  const deviceOptions = engineMeta?.device_options ?? [];
  const batchOptions = engineMeta?.batch_sizes ?? [];
  const quantOptions = engineMeta?.quantizations ?? [];

  useEffect(() => {
    if (!engineMeta) {
      return;
    }

    if (engineMeta.model_options?.choices?.length) {
      const choices = engineMeta.model_options.choices;
      const preferred = engineMeta.model_options.default;
      const fallback = preferred && choices.includes(preferred) ? preferred : choices[0];
      if (!choices.includes(model)) {
        setModel(fallback);
      }
    }

    if (engineMeta.device_options?.length) {
      const existing = engineMeta.device_options.find((opt) => opt.id === device && opt.available);
      if (!existing) {
        const fallback = engineMeta.device_options.find((opt) => opt.available) ?? engineMeta.device_options[0];
        if (fallback) {
          setDevice(fallback.id);
        }
      }
    } else if (device !== "auto") {
      setDevice("auto");
    }

    if (engineMeta.batch_sizes?.length) {
      const choices = engineMeta.batch_sizes;
      if (batchSize === null || !choices.includes(batchSize)) {
        setBatchSize(choices[Math.min(1, choices.length - 1)] ?? choices[0]);
      }
    } else if (batchSize !== null) {
      setBatchSize(null);
    }

    if (engineMeta.quantizations?.length) {
      const preferredQuant = engineMeta.quantizations.find((q) => q.id === "base") ?? engineMeta.quantizations[0];
      if (!quantization || !engineMeta.quantizations.some((q) => q.id === quantization)) {
        setQuantization(preferredQuant.id);
      }
    } else if (quantization !== null) {
      setQuantization(null);
    }
  }, [engineMeta, model, device, batchSize, quantization]);

  useEffect(() => {
    const storedUseCustom = localStorage.getItem("polysub.useCustomKeys");
    const storedOpenai = localStorage.getItem("polysub.openaiKey");
    const storedAssembly = localStorage.getItem("polysub.assemblyKey");
    if (storedUseCustom) setUseCustomKeys(storedUseCustom === "true");
    if (storedOpenai) setOpenaiKey(storedOpenai);
    if (storedAssembly) setAssemblyKey(storedAssembly);
  }, []);

  useEffect(() => {
    localStorage.setItem("polysub.useCustomKeys", String(useCustomKeys));
  }, [useCustomKeys]);

  useEffect(() => {
    localStorage.setItem("polysub.openaiKey", openaiKey);
  }, [openaiKey]);

  useEffect(() => {
    localStorage.setItem("polysub.assemblyKey", assemblyKey);
  }, [assemblyKey]);

  useEffect(() => {
    if (!subtitleDefaults) return;
    setSubtitleLeadIn((prev) => (prev === null ? subtitleDefaults.lead_in : prev));
    setSubtitleLinger((prev) => (prev === null ? subtitleDefaults.linger : prev));
    setSubtitleMinGap((prev) => (prev === null ? subtitleDefaults.min_gap : prev));
    setSubtitleMinDuration((prev) => (prev === null ? subtitleDefaults.min_duration : prev));
    setSubtitleMaxChars((prev) => (prev === null ? subtitleDefaults.max_chars_per_line : prev));
    setSubtitleMaxLines((prev) => (prev === null ? subtitleDefaults.max_lines : prev));
  }, [subtitleDefaults]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Select a media file first");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    const allowedModels = engineMeta?.model_options?.choices ?? [];
    const options: JobOptions = {
      engine,
      local_model_size: allowedModels.length && allowedModels.includes(model) ? model : undefined,
      translation_languages: [],
      translation_model: "none",
      enable_alignment: alignment,
      enable_diarization: diarization,
      output_formats: formats,
      burn_subtitles: false,
    };
    if (engineMeta?.device_options?.length) {
      options.preferred_device = device === "auto" ? undefined : device;
    }
    if (batchSize !== null && (engineMeta?.batch_sizes ?? []).includes(batchSize)) {
      options.batch_size = batchSize;
    } else {
      options.batch_size = undefined;
    }
    if (quantization && quantization !== "base") {
      options.quantization = quantization;
    } else {
      options.quantization = undefined;
    }
    if (engine === "lightning-whisper-mlx") {
      options.subtitle_lead_in = subtitleLeadIn ?? undefined;
      options.subtitle_linger = subtitleLinger ?? undefined;
      options.subtitle_min_gap = subtitleMinGap ?? undefined;
      options.subtitle_min_duration = subtitleMinDuration ?? undefined;
      options.subtitle_max_chars_per_line = subtitleMaxChars ?? undefined;
      options.subtitle_max_lines = subtitleMaxLines ?? undefined;
    }
    if (useCustomKeys) {
      options.openai_api_key = openaiKey.trim() || undefined;
      options.assemblyai_api_key = assemblyKey.trim() || undefined;
    }
    try {
      const job = await createJob(file, options);
      onJobCreated(job);
      setIsSubmitting(false);
    } catch (err: any) {
      setIsSubmitting(false);
      setError(err?.message ?? "Failed to create job");
    }
  };

  const toggleFormat = (value: string) => {
    setFormats((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value]
    );
  };

  const resetSubtitleControls = () => {
    if (!subtitleDefaults) return;
    setSubtitleLeadIn(subtitleDefaults.lead_in);
    setSubtitleLinger(subtitleDefaults.linger);
    setSubtitleMinGap(subtitleDefaults.min_gap);
    setSubtitleMinDuration(subtitleDefaults.min_duration);
    setSubtitleMaxChars(subtitleDefaults.max_chars_per_line);
    setSubtitleMaxLines(subtitleDefaults.max_lines);
  };

  const handleFloatChange = (
    setter: (value: number | null) => void,
    minValue: number | null = 0
  ) =>
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const raw = event.target.value;
      if (raw === "") {
        setter(null);
        return;
      }
      const parsed = Number(raw);
      if (Number.isNaN(parsed)) {
        return;
      }
      const clamped = minValue === null ? parsed : Math.max(minValue, parsed);
      setter(clamped);
    };

  const handleIntChange = (setter: (value: number | null) => void, minValue = 0) =>
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const raw = event.target.value;
      if (raw === "") {
        setter(null);
        return;
      }
      const parsed = Number.parseInt(raw, 10);
      if (Number.isNaN(parsed)) {
        return;
      }
      setter(Math.max(minValue, parsed));
    };

  const assignFile = (newFile: File | undefined) => {
    if (newFile) {
      setFile(newFile);
      setIsDragging(false);
      if (error) setError(null);
    }
  };

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0];
    assignFile(next);
  };

  const onDrop = (event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    const dropped = event.dataTransfer?.files?.[0];
    assignFile(dropped);
  };

  const onDragOver = (event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    if (!isDragging) setIsDragging(true);
  };

  const onDragLeave = (event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setIsDragging(false);
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="flex flex-col gap-6 rounded-3xl border border-slate-800 bg-slate-900/60 p-8 shadow-soft backdrop-blur"
      initial={{ opacity: 0, translateY: 20 }}
      animate={{ opacity: 1, translateY: 0 }}
    >
      <div>
        <h2 className="text-2xl font-semibold text-white">Create a new transcription job</h2>
        <p className="text-sm text-slate-400">
          Everything runs locally except the AI APIs you opt into. Pick your engine and translation targets.
        </p>
        {systemSpecs && (
          <p className="text-xs text-slate-500">
            Detected {systemSpecs.os} ({systemSpecs.arch}) · GPU: {systemSpecs.capabilities.cuda || systemSpecs.capabilities.mps || systemSpecs.capabilities.mlx ? 'available' : 'CPU only'}
          </p>
        )}
      </div>

      <label
        htmlFor="file"
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`flex h-40 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed transition ${
          isDragging
            ? "border-brand bg-slate-900"
            : "border-slate-700 bg-slate-950/40 hover:border-brand hover:bg-slate-900"
        }`}
      >
        <UploadCloud className="mb-2 h-10 w-10 text-brand" />
        <span className="text-sm text-slate-300">
          {file ? file.name : "Drop a movie or audio file, or click to browse"}
        </span>
        <input id="file" type="file" accept="video/*,audio/*" className="hidden" onChange={onFileChange} />
      </label>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="space-y-3">
          <h3 className="font-medium text-slate-200">Transcription engine</h3>
          <select
            value={engine}
            onChange={(event) => setEngine(event.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100"
          >
            {engineOptions.map((option) => (
              <option key={option.value} value={option.value} disabled={option.disabled}>
                {option.label}{option.disabled ? " (unavailable)" : ""}
              </option>
            ))}
          </select>
          {engineMeta && (
            <p className="text-xs text-slate-400">
              {engineMeta.device_options?.some((opt) => opt.id === 'gpu' && opt.available) || engineMeta.device_options?.some((opt) => opt.id === 'mlx' && opt.available)
                ? 'Hardware acceleration available for this engine.'
                : 'Running on CPU fallback for this engine.'}
            </p>
          )}


          {modelChoices.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs uppercase tracking-wide text-slate-400">Model size</span>
              {engineMeta?.model_options?.default && (
                <p className="text-[10px] text-slate-500">Recommended: {engineMeta.model_options.default}</p>
              )}
              <div className="flex flex-wrap gap-2">
                {modelChoices.map((choice) => (
                  <button
                    key={choice}
                    type="button"
                    onClick={() => setModel(choice)}
                    className={`rounded-full px-4 py-1 text-xs transition ${
                      model === choice ? "bg-brand text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    {choice}
                  </button>
                ))}
              </div>
            </div>
          )}

          {deviceOptions.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs uppercase tracking-wide text-slate-400">Device target</span>
              <div className="flex flex-wrap gap-2">
                {deviceOptions.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => option.available && setDevice(option.id)}
                    className={`rounded-full px-4 py-1 text-xs transition ${
                      device === option.id ? "bg-brand text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                    } ${option.available ? '' : 'cursor-not-allowed opacity-50'}`}
                    disabled={!option.available}
                    title={option.available ? undefined : 'Unavailable on this machine'}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {batchOptions.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs uppercase tracking-wide text-slate-400">Batch size</span>
              <div className="flex flex-wrap gap-2">
                {batchOptions.map((size) => (
                  <button
                    key={size}
                    type="button"
                    onClick={() => setBatchSize(size)}
                    className={`rounded-full px-4 py-1 text-xs transition ${
                      batchSize === size ? "bg-brand text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>
          )}

          {quantOptions.length > 0 && engine === "lightning-whisper-mlx" && (
            <div className="space-y-2">
              <span className="text-xs uppercase tracking-wide text-slate-400">Quantization</span>
              <div className="flex flex-wrap gap-2">
                {quantOptions.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setQuantization(option.id)}
                    className={`rounded-full px-4 py-1 text-xs transition ${
                      quantization === option.id ? "bg-brand text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {engine === "lightning-whisper-mlx" && (
            <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs uppercase tracking-wide text-slate-400">Subtitle timing</span>
                  <p className="text-[11px] text-slate-500">
                    Adjust how early captions appear, how long they linger, and layout limits.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={resetSubtitleControls}
                  disabled={!subtitleDefaults}
                  className="rounded-full border border-slate-700 px-3 py-1 text-[11px] text-slate-300 transition hover:border-brand hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reset
                </button>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="space-y-1 text-xs text-slate-300">
                  <span>Lead-in (seconds)</span>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={subtitleLeadIn ?? ""}
                    onChange={handleFloatChange(setSubtitleLeadIn, 0)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
                  />
                </label>
                <label className="space-y-1 text-xs text-slate-300">
                  <span>Linger (seconds)</span>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={subtitleLinger ?? ""}
                    onChange={handleFloatChange(setSubtitleLinger, 0)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
                  />
                </label>
                <label className="space-y-1 text-xs text-slate-300">
                  <span>Minimum gap (seconds)</span>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={subtitleMinGap ?? ""}
                    onChange={handleFloatChange(setSubtitleMinGap, 0)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
                  />
                </label>
                <label className="space-y-1 text-xs text-slate-300">
                  <span>Minimum duration (seconds)</span>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={subtitleMinDuration ?? ""}
                    onChange={handleFloatChange(setSubtitleMinDuration, 0)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
                  />
                </label>
                <label className="space-y-1 text-xs text-slate-300">
                  <span>Max characters per line</span>
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={subtitleMaxChars ?? ""}
                    onChange={handleIntChange(setSubtitleMaxChars, 0)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
                  />
                </label>
                <label className="space-y-1 text-xs text-slate-300">
                  <span>Max lines per caption</span>
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={subtitleMaxLines ?? ""}
                    onChange={handleIntChange(setSubtitleMaxLines, 0)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
                  />
                </label>
              </div>
            </div>
          )}

          {engine === "whisperx" && (
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm text-slate-200">
                <input
                  type="checkbox"
                  checked={alignment}
                  onChange={(event) => setAlignment(event.target.checked)}
                  className="rounded border border-slate-600 bg-slate-900"
                />
                Run alignment (WhisperX)
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-200">
                <input
                  type="checkbox"
                  checked={diarization}
                  onChange={(event) => setDiarization(event.target.checked)}
                  className="rounded border border-slate-600 bg-slate-900"
                />
                Enable speaker diarization
              </label>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <h3 className="font-medium text-slate-200">Outputs</h3>
          <div className="space-y-2">
            <span className="text-xs uppercase tracking-wide text-slate-400">Outputs</span>
            <div className="flex gap-3 text-sm text-slate-200">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formats.includes("srt")}
                  onChange={() => toggleFormat("srt")}
                  className="rounded border border-slate-600 bg-slate-900"
                />
                SRT
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formats.includes("vtt")}
                  onChange={() => toggleFormat("vtt")}
                  className="rounded border border-slate-600 bg-slate-900"
                />
                VTT
              </label>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            Need translated captions? Trigger translation from the job card after transcription finishes.
          </p>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-white">API keys</h3>
            <p className="text-xs text-slate-400">
              Optional: provide keys here if you prefer not to store them in `.env`. Keys stay on this device via local storage.
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-200">
            <input
              type="checkbox"
              checked={useCustomKeys}
              onChange={(event) => setUseCustomKeys(event.target.checked)}
              className="rounded border border-slate-600 bg-slate-900"
            />
            Enable
          </label>
        </div>

        {useCustomKeys && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="text-xs uppercase tracking-wide text-slate-400">OpenAI API Key</label>
              <input
                type="password"
                value={openaiKey}
                placeholder="sk-..."
                onChange={(event) => setOpenaiKey(event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs uppercase tracking-wide text-slate-400">AssemblyAI API Key</label>
              <input
                type="password"
                value={assemblyKey}
                placeholder="assemblyai-..."
                onChange={(event) => setAssemblyKey(event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
              />
            </div>
          </div>
        )}
      </section>

      {error && <p className="rounded-lg border border-red-500/40 bg-red-900/30 px-4 py-2 text-sm text-red-200">{error}</p>}

      <button
        type="submit"
        disabled={isSubmitting || !file}
        className="group flex items-center justify-center gap-2 rounded-full bg-brand px-6 py-3 text-sm font-semibold text-white shadow-soft transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" /> Launching job...
          </>
        ) : (
          <>
            <UploadCloud className="h-4 w-4 transition group-hover:-translate-y-0.5" />
            Create job
          </>
        )}
      </button>
    </motion.form>
  );
}
