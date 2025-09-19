"use client";

import useSWR from "swr";
import type { Job } from "./types";
import { fetchJobs } from "./api";

export function useJobs() {
  const { data, error, isLoading, mutate } = useSWR<Job[]>("jobs", fetchJobs, {
    refreshInterval: 4000,
  });

  return {
    jobs: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}
