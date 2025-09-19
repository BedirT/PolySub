export type JobStatus =
  | "queued"
  | "processing"
  | "transcribing"
  | "aligning"
  | "translating"
  | "exporting"
  | "completed"
  | "failed"
  | "cancelled";

export interface JobProgress {
  percent: number;
  stage: JobStatus;
  message: string;
}

export interface Artifact {
  kind: string;
  path: string;
  label: string;
}

export interface JobOptions {
  engine: string;
  local_model_size?: string | null;
  translation_languages: string[];
  translation_model: string;
  enable_alignment: boolean;
  enable_diarization: boolean;
  output_formats: string[];
  burn_subtitles: boolean;
  openai_api_key?: string | null;
  assemblyai_api_key?: string | null;
  preferred_device?: string | null;
  batch_size?: number | null;
  quantization?: string | null;
  subtitle_lead_in?: number | null;
  subtitle_linger?: number | null;
  subtitle_min_gap?: number | null;
  subtitle_min_duration?: number | null;
  subtitle_max_chars_per_line?: number | null;
  subtitle_max_lines?: number | null;
}

export interface TranslationRequest {
  languages: string[];
  model: string;
  openai_api_key?: string | null;
}

export interface EngineDeviceOption {
  id: string;
  label: string;
  available: boolean;
}

export interface EngineSpecs {
  device_options: EngineDeviceOption[];
  model_options: {
    default: string | null;
    choices: string[];
  };
  batch_sizes: number[];
  quantizations?: { id: string; label: string }[];
  available?: boolean;
}

export interface SystemSpecs {
  os: string;
  arch: string;
  cpu_count: number | null;
  capabilities: {
    cuda: boolean;
    mps: boolean;
    mlx: boolean;
  };
  engines: Record<string, EngineSpecs>;
  subtitle_defaults?: {
    lead_in: number;
    linger: number;
    min_gap: number;
    min_duration: number;
    max_chars_per_line: number;
    max_lines: number;
  };
}

export interface Job {
  id: string;
  created_at: string;
  updated_at: string;
  status: JobStatus;
  options: JobOptions;
  source_path: string;
  audio_path?: string;
  transcript_json?: string;
  summary?: string;
  artifacts: Artifact[];
  progress: JobProgress;
  error?: string;
}
