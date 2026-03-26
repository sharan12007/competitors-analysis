"use client";

import { motion } from "framer-motion";
import { Github, Star } from "lucide-react";
import type { EventData } from "@/lib/sse";

type GithubAlternativesProps = {
  repos: EventData[];
};

export function GithubAlternatives({ repos }: GithubAlternativesProps) {
  const sorted = [...repos].sort((a, b) => Number(b.stars ?? 0) - Number(a.stars ?? 0));

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="dashboard-panel flex h-[calc(58vh-2rem)] flex-col"
    >
      <div className="panel-header">
        <div>
          <p className="eyebrow mb-1">Open Source Radar</p>
          <h2 className="panel-title">GitHub alternatives</h2>
        </div>
        <Github className="h-5 w-5 text-[var(--muted)]" />
      </div>

      <div className="mt-5 flex-1 space-y-3 overflow-y-auto pr-2">
        {sorted.length ? (
          sorted.map((repo, index) => (
            <a
              key={`${String(repo.url ?? repo.name ?? "repo")}-${index}`}
              href={String(repo.url ?? "#")}
              target="_blank"
              rel="noreferrer"
              className="github-card"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-[var(--text)]">{String(repo.name ?? "Repository")}</div>
                  <div className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--muted)]">
                    {String(repo.description ?? "No description available.")}
                  </div>
                </div>
                <div className="flex items-center gap-1 rounded-full bg-[rgba(29,107,99,0.1)] px-2 py-1 text-xs text-[var(--accent)]">
                  <Star className="h-3.5 w-3.5" />
                  {Number(repo.stars ?? 0).toLocaleString()}
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2 text-xs text-[var(--muted)]">
                <span className="repo-pill">{String(repo.language ?? "Unknown")}</span>
                <span className="repo-pill">Updated {String(repo.last_updated ?? "N/A")}</span>
              </div>
            </a>
          ))
        ) : (
          <div className="empty-note">GitHub alternatives will appear here once the search completes.</div>
        )}
      </div>
    </motion.section>
  );
}
