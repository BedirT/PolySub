import axios from "axios";
import type { Job, JobOptions, SystemSpecs, TranslationRequest } from "./types";

const baseURL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

const client = axios.create({
  baseURL,
});

export async function fetchJobs(): Promise<Job[]> {
  const response = await client.get<Job[]>("/jobs");
  return response.data;
}

export async function fetchJob(id: string): Promise<Job> {
  const response = await client.get<Job>(`/jobs/${id}`);
  return response.data;
}

export async function cancelJob(id: string): Promise<void> {
  await client.post(`/jobs/${id}/cancel`);
}

export async function createJob(file: File, options: JobOptions): Promise<Job> {
  const form = new FormData();
  form.append("file", file);
  form.append("options", JSON.stringify(options));
  const response = await client.post<Job>("/jobs", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function fetchSystemSpecs(): Promise<SystemSpecs> {
  const response = await client.get<SystemSpecs>("/system/specs");
  return response.data;
}

export async function triggerTranslation(jobId: string, payload: TranslationRequest): Promise<Job> {
  const response = await client.post<Job>(`/jobs/${jobId}/translate`, payload);
  return response.data;
}
