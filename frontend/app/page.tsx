"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { JobCreator } from "../components/JobCreator";
import { JobList } from "../components/JobList";
import { useJobs } from "../lib/use-jobs";
import type { Job } from "../lib/types";

export default function Home() {
  const { jobs, refresh, isLoading } = useJobs();

  const handleJobCreated = useCallback(
    (job: Job) => {
      refresh();
    },
    [refresh]
  );

  return (
    <div className="min-h-screen bg-slate-950 pb-24">
      <div className="relative mx-auto flex max-w-6xl flex-col gap-10 px-6 pt-16">
        <motion.div
          initial={{ opacity: 0, translateY: -16 }}
          animate={{ opacity: 1, translateY: 0 }}
          className="space-y-4"
        >
          <span className="rounded-full border border-brand/30 bg-brand/10 px-3 py-1 text-xs uppercase tracking-wide text-brand">
            PolySub Studio
          </span>
          <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Transcribe. Translate. Subtitle.<br className="hidden sm:block" /> Locally, with AI assistance.
          </h1>
          <p className="max-w-2xl text-sm text-slate-400">
            Choose between open-source pipelines like Faster Whisper and WhisperX or leverage OpenAI and AssemblyAI when you
            need cloud accuracy. Progress is tracked at every stage with artifacts stored safely on your machine.
          </p>
        </motion.div>

        <JobCreator onJobCreated={handleJobCreated} />

        <section className="space-y-4">
          <header className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Recent jobs</h2>
            {isLoading && <span className="text-xs text-slate-400">Refreshing...</span>}
          </header>
          <JobList jobs={jobs} onRefresh={refresh} />
        </section>
      </div>
    </div>
  );
}
