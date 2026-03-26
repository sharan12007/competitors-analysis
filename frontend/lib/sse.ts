"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type EventData = {
  [key: string]: unknown;
  message?: unknown;
  competitors?: unknown;
  repos?: unknown;
  chunk?: unknown;
  pdf_url?: unknown;
  json_url?: unknown;
  name?: unknown;
  competitor?: unknown;
  competitor_name?: unknown;
};

export type StreamEvent = {
  type: string;
  data: EventData;
};

type CompetitorSummary = EventData;
type RepoSummary = EventData;
type SynthesisSummary = EventData | null;
type ExportUrls = { pdf_url: string | null; json_url: string | null } | null;
type HookStatus = "idle" | "connecting" | "streaming" | "complete" | "error";

type UseSSEResult = {
  events: StreamEvent[];
  status: HookStatus;
  competitorList: EventData[];
  browserSteps: EventData[];
  browserDone: boolean;
  analyzedCompetitors: Record<string, CompetitorSummary>;
  githubRepos: RepoSummary[];
  thoughtStream: string;
  synthesis: SynthesisSummary;
  exportUrls: ExportUrls;
  statusMessage: string;
};

export function useSSE(sessionId: string | null): UseSSEResult {
  const eventSourceRef = useRef<EventSource | null>(null);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [status, setStatus] = useState<HookStatus>("idle");
  const [competitorList, setCompetitorList] = useState<EventData[]>([]);
  const [browserSteps, setBrowserSteps] = useState<EventData[]>([]);
  const [browserDone, setBrowserDone] = useState(false);
  const [analyzedCompetitors, setAnalyzedCompetitors] = useState<Record<string, CompetitorSummary>>({});
  const [githubRepos, setGithubRepos] = useState<RepoSummary[]>([]);
  const [thoughtStream, setThoughtStream] = useState("");
  const [synthesis, setSynthesis] = useState<SynthesisSummary>(null);
  const [exportUrls, setExportUrls] = useState<ExportUrls>(null);
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    if (!sessionId) {
      setStatus("idle");
      return;
    }

    setEvents([]);
    setStatus("connecting");
    setCompetitorList([]);
    setBrowserSteps([]);
    setBrowserDone(false);
    setAnalyzedCompetitors({});
    setGithubRepos([]);
    setThoughtStream("");
    setSynthesis(null);
    setExportUrls(null);
    setStatusMessage("");

    const source = new EventSource(`${API_BASE}/stream/${sessionId}`);
    eventSourceRef.current = source;

    source.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as StreamEvent;
        console.log(parsed.type, parsed.data);

        setStatus((current) => (current === "connecting" ? "streaming" : current));
        setEvents((prev) => [...prev, parsed]);

        switch (parsed.type) {
          case "status":
            setStatusMessage(String(parsed.data?.message ?? ""));
            break;
          case "competitors_found":
            if (Array.isArray(parsed.data?.competitors)) {
              setCompetitorList(parsed.data.competitors as EventData[]);
            }
            break;
          case "browser_step":
            setBrowserSteps((prev) => [...prev, parsed.data]);
            break;
          case "browser_complete":
            setBrowserDone(true);
            setAnalyzedCompetitors((prev) => {
              const competitorName = String(
                parsed.data?.name ??
                parsed.data?.competitor ??
                parsed.data?.competitor_name ??
                `competitor_${Object.keys(prev).length + 1}`
              );
              const existing = prev[competitorName] ?? {};
              return {
                ...prev,
                [competitorName]: {
                  ...existing,
                  ...parsed.data,
                  name: competitorName,
                  browser_findings: parsed.data?.findings ?? existing.browser_findings ?? "",
                  steps_taken: parsed.data?.steps_taken ?? existing.steps_taken ?? 0,
                  is_browser_analyzed: true,
                  market_position:
                    existing.market_position ??
                    `Analyzed via browser agent (${String(parsed.data?.steps_taken ?? 0)} steps)`,
                },
              };
            });
            break;
          case "competitor_analyzed":
            setAnalyzedCompetitors((prev) => {
              const competitorName = String(
                parsed.data?.name ??
                parsed.data?.competitor ??
                parsed.data?.competitor_name ??
                `competitor_${Object.keys(prev).length + 1}`
              );
              return {
                ...prev,
                [competitorName]: parsed.data,
              };
            });
            break;
          case "github_results":
            if (Array.isArray(parsed.data?.repos)) {
              setGithubRepos(parsed.data.repos as RepoSummary[]);
            }
            break;
          case "chain_of_thought":
          case "synthesis_chunk":
            setThoughtStream((prev) => prev + String(parsed.data?.chunk ?? ""));
            break;
          case "synthesis":
            setSynthesis(parsed.data);
            break;
          case "export_ready":
            setExportUrls({
              pdf_url: typeof parsed.data?.pdf_url === "string" ? parsed.data.pdf_url : null,
              json_url: typeof parsed.data?.json_url === "string" ? parsed.data.json_url : null,
            });
            break;
          case "complete":
            setStatus("complete");
            source.close();
            eventSourceRef.current = null;
            break;
          case "error":
            setStatus("error");
            source.close();
            eventSourceRef.current = null;
            break;
          default:
            break;
        }
      } catch {
        setStatus("error");
        source.close();
        eventSourceRef.current = null;
      }
    };

    source.onerror = () => {
      setStatus("error");
      source.close();
      eventSourceRef.current = null;
    };

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [sessionId]);

  return {
    events,
    status,
    competitorList,
    browserSteps,
    browserDone,
    analyzedCompetitors,
    githubRepos,
    thoughtStream,
    synthesis,
    exportUrls,
    statusMessage,
  };
}
