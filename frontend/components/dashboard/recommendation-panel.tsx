"use client";

import { useState, type ReactNode } from "react";
import { CheckCircle2, ChevronDown, CircleX, Sparkles } from "lucide-react";
import clsx from "clsx";
import type { EventData } from "@/lib/sse";

type RecommendationPanelProps = {
  synthesis: EventData | null;
};

function toList(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function Section({
  title,
  defaultOpen = true,
  icon,
  items,
  numbered = false,
}: {
  title: string;
  defaultOpen?: boolean;
  icon: ReactNode;
  items: string[];
  numbered?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-3xl border border-[var(--line)] bg-white/55">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3 text-sm font-medium text-[var(--text)]">
          {icon}
          {title}
        </div>
        <ChevronDown className={clsx("h-4 w-4 text-[var(--muted)] transition", open && "rotate-180")} />
      </button>

      {open ? (
        <div className="border-t border-[var(--line)] px-5 py-4">
          {items.length ? (
            <div className="space-y-3 text-sm leading-6 text-[var(--muted)]">
              {items.map((item, index) => (
                <div key={`${title}-${item}`} className="flex gap-3">
                  <div className="mt-0.5 shrink-0 text-[var(--brand)]">{numbered ? `${index + 1}.` : "-"}</div>
                  <div>{item}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-note">No items available yet.</div>
          )}
        </div>
      ) : null}
    </div>
  );
}

export function RecommendationPanel({ synthesis }: RecommendationPanelProps) {
  const marketSummary = String(synthesis?.market_summary ?? "");
  const advantages = toList(synthesis?.advantages);
  const gaps = toList(synthesis?.gaps);
  const recommendations = toList(synthesis?.recommendations);
  const pricingStrategy = String(synthesis?.pricing_strategy ?? "");

  return (
    <section className="dashboard-panel flex flex-col">
      <div className="panel-header">
        <div>
          <p className="eyebrow mb-1">Recommendations</p>
          <h2 className="panel-title">Strategic takeaways</h2>
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <div className="rounded-3xl border border-[var(--line)] bg-white/55 px-5 py-4">
          <div className="mb-2 text-sm font-medium text-[var(--text)]">Market summary</div>
          <div className="text-sm leading-6 text-[var(--muted)]">
            {marketSummary || "Market summary will appear here when synthesis completes."}
          </div>
        </div>

        <Section title="Our Advantages" icon={<CheckCircle2 className="h-4 w-4 text-emerald-600" />} items={advantages} />
        <Section title="Our Gaps" icon={<CircleX className="h-4 w-4 text-rose-600" />} items={gaps} defaultOpen={false} />
        <Section title="Top Recommendations" icon={<Sparkles className="h-4 w-4 text-[var(--brand)]" />} items={recommendations} numbered />

        <div className="rounded-3xl border border-amber-200 bg-amber-50 px-5 py-4">
          <div className="mb-2 text-sm font-medium text-amber-900">Pricing strategy</div>
          <div className="border-l-4 border-amber-400 pl-4 text-sm leading-6 text-amber-900">
            {pricingStrategy || "Pricing strategy will appear here when synthesis completes."}
          </div>
        </div>
      </div>
    </section>
  );
}
