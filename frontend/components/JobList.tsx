"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { Job } from "../lib/types";
import { JobCard } from "./JobCard";

interface Props {
  jobs: Job[];
  onRefresh(): void;
}

export function JobList({ jobs, onRefresh }: Props) {
  if (jobs.length === 0) {
    return (
      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-12 text-center text-slate-400">
        Upload a video to see transcription progress here.
      </div>
    );
  }

  return (
    <AnimatePresence>
      <motion.div className="grid gap-4 xl:grid-cols-2">
        {jobs.map((job) => (
          <JobCard key={job.id} job={job} onRefresh={onRefresh} />
        ))}
      </motion.div>
    </AnimatePresence>
  );
}
