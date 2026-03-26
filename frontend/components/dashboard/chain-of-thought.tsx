"use client";

import { useEffect, useMemo, useRef } from "react";
import type { EventData } from "@/lib/sse";

type ChainOfThoughtProps = {
  thoughtStream: string;
  status: "idle" | "connecting" | "streaming" | "complete" | "error";
  synthesis?: EventData | null;
};

type Segment = {
  type: "thinking" | "body";
  content: string;
};

function parseThoughts(text: string): Segment[] {
  const regex = /(\[THINKING:[^\]]*\])/g;
  const parts = text.split(regex).filter(Boolean);

  return parts.map((part) => ({
    type: part.startsWith("[THINKING:") ? "thinking" : "body",
    content: part,
  }));
}

function buildRenderableFallback(synthesis?: EventData | null) {
  if (!synthesis) {
    return "";
  }

  const sections: string[] = [];
  const marketSummary = typeof synthesis.market_summary === "string" ? synthesis.market_summary : "";
  const pricingStrategy = typeof synthesis.pricing_strategy === "string" ? synthesis.pricing_strategy : "";
  const advantages = Array.isArray(synthesis.advantages) ? synthesis.advantages.map((item) => String(item)) : [];
  const gaps = Array.isArray(synthesis.gaps) ? synthesis.gaps.map((item) => String(item)) : [];
  const recommendations = Array.isArray(synthesis.recommendations) ? synthesis.recommendations.map((item) => String(item)) : [];

  if (marketSummary) {
    sections.push("[THINKING: Final synthesis was available even though live reasoning chunks were not captured.]");
    sections.push("## Market Summary");
    sections.push(marketSummary);
  }
  if (advantages.length) {
    sections.push("[THINKING: Reconstructed advantage reasoning from the completed synthesis output.]");
    sections.push("## Our Competitive Advantages");
    sections.push(advantages.map((item) => `- ${item}`).join("\n"));
  }
  if (gaps.length) {
    sections.push("[THINKING: Reconstructed blind spots from the completed synthesis output.]");
    sections.push("## Our Gaps and Blind Spots");
    sections.push(gaps.map((item) => `- ${item}`).join("\n"));
  }
  if (pricingStrategy) {
    sections.push("[THINKING: Pricing reasoning reconstructed from the final synthesis payload.]");
    sections.push("## Pricing Strategy Recommendation");
    sections.push(pricingStrategy);
  }
  if (recommendations.length) {
    sections.push("[THINKING: Recommended actions reconstructed from the final synthesis payload.]");
    sections.push("## Top 5 Prioritized Recommendations");
    sections.push(recommendations.map((item, index) => `${index + 1}. ${item}`).join("\n"));
  }

  return sections.join("\n\n").trim();
}

export function ChainOfThought({ thoughtStream, status, synthesis }: ChainOfThoughtProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const displayText = useMemo(() => {
    if (thoughtStream.trim()) {
      return thoughtStream;
    }
    return buildRenderableFallback(synthesis);
  }, [thoughtStream, synthesis]);
  const segments = useMemo(() => parseThoughts(displayText), [displayText]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [displayText]);

  return (
    <section className="dashboard-panel flex h-[48vh] flex-col">
      <div className="panel-header">
        <div>
          <p className="eyebrow mb-1">Reasoning Stream</p>
          <h2 className="panel-title">Chain of thought</h2>
        </div>
      </div>

      <div className="mt-5 flex-1 overflow-y-auto pr-2">
        {segments.length ? (
          <div className="space-y-4">
            {segments.map((segment, index) =>
              segment.type === "thinking" ? (
                <div key={`${segment.content}-${index}`} className="thought-block">
                  <span className="mr-2">Thinking:</span>
                  {segment.content}
                </div>
              ) : (
                <div key={`${segment.content}-${index}`} className="thought-text">
                  {segment.content}
                </div>
              )
            )}
            {status === "streaming" ? <span className="blinking-cursor" /> : null}
          </div>
        ) : (
          <div className="empty-note">Strategic synthesis will appear here once the analysis finishes.</div>
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
