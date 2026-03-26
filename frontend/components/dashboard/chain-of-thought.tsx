"use client";

import { useEffect, useMemo, useRef } from "react";

type ChainOfThoughtProps = {
  thoughtStream: string;
  status: "idle" | "connecting" | "streaming" | "complete" | "error";
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

export function ChainOfThought({ thoughtStream, status }: ChainOfThoughtProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const segments = useMemo(() => parseThoughts(thoughtStream), [thoughtStream]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [thoughtStream]);

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
          <div className="empty-note">Strategic synthesis will stream here as soon as the LLM starts responding.</div>
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
