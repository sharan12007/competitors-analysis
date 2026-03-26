"use client";

import Link from "next/link";
import { CheckCircle2, LoaderCircle, Siren } from "lucide-react";
import clsx from "clsx";

type StatusBarProps = {
  status: "idle" | "connecting" | "streaming" | "complete" | "error";
  statusMessage: string;
  sessionId: string;
};

export function StatusBar({ status, statusMessage, sessionId }: StatusBarProps) {
  const label =
    status === "complete"
      ? "Analysis complete"
      : status === "error"
        ? "Stream error"
        : status === "connecting"
          ? "Connecting to live stream"
          : statusMessage || "Waiting for analysis events";

  return (
    <div className="status-bar">
      <div className="shell flex h-full min-w-[1280px] items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <div
            className={clsx(
              "status-indicator",
              status === "streaming" && "is-streaming",
              status === "complete" && "is-complete",
              status === "error" && "is-error"
            )}
          >
            {status === "complete" ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : status === "error" ? (
              <Siren className="h-4 w-4" />
            ) : (
              <LoaderCircle className={clsx("h-4 w-4", status === "streaming" && "animate-spin")} />
            )}
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Live Analysis</div>
            <div className="text-sm font-medium text-[var(--text)]">{label}</div>
          </div>
        </div>

        <div className="rounded-full border border-[var(--line)] bg-white/5 px-4 py-2 text-xs text-[var(--muted)]">
          Session: <span className="font-medium text-[var(--text)]">{sessionId}</span>
        </div>
        <Link
          href="/"
          className="rounded-full border border-[var(--line)] bg-white/5 px-4 py-2 text-xs font-medium text-[var(--text)] transition hover:border-[var(--brand)] hover:text-[var(--brand)]"
        >
          Research Again
        </Link>
      </div>
    </div>
  );
}
