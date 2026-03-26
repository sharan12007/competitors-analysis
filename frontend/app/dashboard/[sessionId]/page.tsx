"use client";

import { useParams } from "next/navigation";
import { useSSE } from "@/lib/sse";
import { BrowserAgentFeed } from "@/components/dashboard/browser-agent-feed";
import { ChainOfThought } from "@/components/dashboard/chain-of-thought";
import { ComparisonMatrix } from "@/components/dashboard/comparison-matrix";
import { CompetitorCardList } from "@/components/dashboard/competitor-card";
import { ExportBar } from "@/components/dashboard/export-bar";
import { GithubAlternatives } from "@/components/dashboard/github-alternatives";
import { RecommendationPanel } from "@/components/dashboard/recommendation-panel";
import { StatusBar } from "@/components/dashboard/status-bar";

export default function DashboardPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = typeof params?.sessionId === "string" ? params.sessionId : null;
  const {
    status,
    statusMessage,
    competitorList,
    browserSteps,
    browserDone,
    analyzedCompetitors,
    githubRepos,
    thoughtStream,
    synthesis,
    exportUrls,
  } = useSSE(sessionId);

  if (!sessionId) {
    return null;
  }

  return (
    <>
      <StatusBar status={status} statusMessage={statusMessage} sessionId={sessionId} />

      <main className="dashboard-shell">
        <div className="dashboard-grid">
          <div className="dashboard-column">
            <BrowserAgentFeed steps={browserSteps} browserDone={browserDone} />
            <GithubAlternatives repos={githubRepos} />
          </div>

          <div className="dashboard-column">
            <CompetitorCardList competitors={competitorList} analyzedCompetitors={analyzedCompetitors} />
            <ComparisonMatrix synthesis={synthesis} />
          </div>

          <div className="dashboard-column">
            <ChainOfThought thoughtStream={thoughtStream} status={status} />
            <RecommendationPanel synthesis={synthesis} />
            <ExportBar exportUrls={exportUrls} />
          </div>
        </div>
      </main>
    </>
  );
}
