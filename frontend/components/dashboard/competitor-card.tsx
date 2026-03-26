"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Bot, ExternalLink } from "lucide-react";
import clsx from "clsx";
import type { EventData } from "@/lib/sse";

type CompetitorCardListProps = {
  competitors: EventData[];
  analyzedCompetitors: Record<string, EventData>;
};

function pricingTone(model: string) {
  switch (model) {
    case "free":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "freemium":
      return "bg-sky-100 text-sky-800 border-sky-200";
    case "paid":
      return "bg-amber-100 text-amber-800 border-amber-200";
    case "enterprise":
      return "bg-violet-100 text-violet-800 border-violet-200";
    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
}

function normalizedFeatures(value: unknown) {
  return Array.isArray(value) ? value.slice(0, 6).map((item) => String(item)) : [];
}

function normalizedList(value: unknown) {
  return Array.isArray(value) ? value.slice(0, 3).map((item) => String(item)) : [];
}

function BrowserFindingsPreview({ findings }: { findings: string }) {
  if (!findings) {
    return null;
  }

  return (
    <div className="mt-4 rounded-2xl border border-[rgba(85,68,149,0.16)] bg-[rgba(92,78,158,0.06)] px-4 py-3 text-sm leading-6 text-[var(--muted)]">
      {findings.slice(0, 360)}
      {findings.length > 360 ? "..." : ""}
    </div>
  );
}

function SkeletonCard({ name }: { name: string }) {
  return (
    <div className="competitor-card skeleton-card">
      <div className="flex items-center justify-between">
        <div className="shimmer h-6 w-40 rounded-full bg-[rgba(92,75,52,0.08)]" />
        <div className="shimmer h-6 w-24 rounded-full bg-[rgba(92,75,52,0.08)]" />
      </div>
      <div className="shimmer mt-4 h-4 w-32 rounded-full bg-[rgba(92,75,52,0.08)]" />
      <div className="shimmer mt-4 h-16 rounded-2xl bg-[rgba(92,75,52,0.08)]" />
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="shimmer h-24 rounded-2xl bg-[rgba(92,75,52,0.08)]" />
        <div className="shimmer h-24 rounded-2xl bg-[rgba(92,75,52,0.08)]" />
      </div>
      <div className="mt-3 text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{name}</div>
    </div>
  );
}

export function CompetitorCardList({ competitors, analyzedCompetitors }: CompetitorCardListProps) {
  return (
    <section className="space-y-4">
      <div className="px-1">
        <p className="eyebrow mb-1">Competitors</p>
        <h2 className="panel-title">Live market profiles</h2>
      </div>

      <AnimatePresence initial={false}>
        {competitors.map((competitor, index) => {
          const name = String(competitor.name ?? `Competitor ${index + 1}`);
          const normalized = analyzedCompetitors[name];

          if (!normalized) {
            return <SkeletonCard key={`skeleton-${name}`} name={name} />;
          }

          const pricingModel = String(normalized.pricing_model ?? "unknown").toLowerCase();
          const pricingDetails = String(normalized.pricing_details ?? "");
          const marketPosition = String(normalized.market_position ?? "No market position available.");
          const url = String(normalized.url ?? competitor.url ?? "#");
          const features = normalizedFeatures(normalized.features);
          const strengths = normalizedList(normalized.strengths);
          const weaknesses = normalizedList(normalized.weaknesses);
          const browserFindings = String(normalized.browser_findings ?? "");
          const isBrowserAnalyzed = Boolean(normalized.is_browser_analyzed);
          const targetAudience = String(normalized.target_audience ?? "");

          return (
            <motion.article
              key={name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              className={clsx("competitor-card", isBrowserAnalyzed && "browser-card")}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="text-2xl text-[var(--text)]">{name}</h3>
                    {isBrowserAnalyzed ? (
                      <span className="browser-badge">
                        <Bot className="h-3.5 w-3.5" />
                        Browser Analyzed
                      </span>
                    ) : null}
                  </div>
                  <a href={url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-2 text-sm text-[var(--accent)]">
                    <span className="truncate">{url}</span>
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
                <span className={clsx("pricing-pill", pricingTone(pricingModel))}>{pricingModel}</span>
              </div>

              <p className="mt-4 text-sm italic leading-6 text-[var(--muted)]">{marketPosition}</p>

              {pricingDetails ? (
                <div className="mt-4 rounded-2xl border border-[var(--line)] bg-white/65 px-4 py-3 text-sm leading-6 text-[var(--muted)]">
                  <span className="font-medium text-[var(--text)]">Pricing:</span> {pricingDetails}
                </div>
              ) : null}

              {targetAudience ? (
                <div className="mt-3 rounded-2xl border border-[var(--line)] bg-white/65 px-4 py-3 text-sm leading-6 text-[var(--muted)]">
                  <span className="font-medium text-[var(--text)]">Target audience:</span> {targetAudience}
                </div>
              ) : null}

              <div className="mt-5">
                <div className="mb-3 text-sm font-medium text-[var(--text)]">Top features</div>
                <div className="flex flex-wrap gap-2">
                  {features.length ? (
                    features.map((feature) => (
                      <span key={feature} className="feature-pill">
                        {feature}
                      </span>
                    ))
                  ) : (
                    <span className="empty-note">Feature extraction still in progress.</span>
                  )}
                </div>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="insight-box">
                  <div className="mb-3 text-sm font-medium text-[var(--text)]">Strengths</div>
                  {strengths.length ? (
                    <ul className="space-y-2 text-sm leading-6 text-[var(--muted)]">
                      {strengths.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="empty-note">No strengths extracted yet.</div>
                  )}
                </div>

                <div className="insight-box">
                  <div className="mb-3 text-sm font-medium text-[var(--text)]">Weaknesses</div>
                  {weaknesses.length ? (
                    <ul className="space-y-2 text-sm leading-6 text-[var(--muted)]">
                      {weaknesses.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="empty-note">No weaknesses extracted yet.</div>
                  )}
                </div>
              </div>

              {isBrowserAnalyzed ? <BrowserFindingsPreview findings={browserFindings} /> : null}
            </motion.article>
          );
        })}
      </AnimatePresence>
    </section>
  );
}
