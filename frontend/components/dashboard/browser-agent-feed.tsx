"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, CheckCircle2, Globe } from "lucide-react";
import type { EventData } from "@/lib/sse";

type BrowserAgentFeedProps = {
  steps: EventData[];
  browserDone: boolean;
};

export function BrowserAgentFeed({ steps, browserDone }: BrowserAgentFeedProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [steps.length, browserDone]);

  return (
    <section className="dashboard-panel flex h-[42vh] flex-col">
      <div className="panel-header">
        <div>
          <p className="eyebrow mb-1">Browser Agent</p>
          <h2 className="panel-title">Live browser trace</h2>
        </div>
        <div className="rounded-full border border-[var(--line)] bg-white/60 px-3 py-1 text-xs text-[var(--muted)]">
          {steps.length} steps
        </div>
      </div>

      <div className="mt-5 flex-1 overflow-y-auto pr-2">
        <AnimatePresence initial={false}>
          {steps.map((step, index) => {
            const stepNumber = typeof step.step === "number" ? step.step : index + 1;
            const action = String(step.action ?? "Observing browser activity");
            const url = typeof step.url === "string" ? step.url : "";

            return (
              <motion.div
                key={`${stepNumber}-${action}-${index}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.15 }}
                className="browser-step-card"
              >
                <div className="browser-step-badge">{stepNumber}</div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start gap-2 text-sm text-[var(--text)]">
                    <Bot className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                    <span>{action}</span>
                  </div>
                  {url ? (
                    <div className="mt-2 flex items-center gap-2 text-xs text-[var(--muted)]">
                      <Globe className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{url}</span>
                    </div>
                  ) : null}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {browserDone ? (
          <div className="mt-4 flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <CheckCircle2 className="h-4 w-4" />
            Browser Analysis Complete
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
