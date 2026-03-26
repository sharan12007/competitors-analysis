"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startAnalysis } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [productName, setProductName] = useState("Linear");
  const [productDescription, setProductDescription] = useState("Project management software for software teams");
  const [productUrl, setProductUrl] = useState("");
  const [differentiators, setDifferentiators] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit() {
    setLoading(true);
    setError("");

    try {
      const sessionId = await startAnalysis({
        product_name: productName,
        product_description: productDescription,
        product_url: productUrl || undefined,
        differentiators: differentiators || undefined,
      });
      router.push(`/dashboard/${sessionId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell px-4 py-8 md:px-0 md:py-10">
      <section className="mb-6 rounded-[32px] border border-[var(--line)] bg-[rgba(255,248,238,0.72)] px-6 py-8 shadow-[var(--shadow)] md:px-10 md:py-12">
        <p className="eyebrow mb-3">Competitor Intelligence Engine</p>
        <div className="grid gap-8 md:grid-cols-[1.2fr_0.8fr] md:items-end">
          <div>
            <h1 className="max-w-3xl text-4xl leading-tight md:text-6xl">
              Turn a plain product brief into a live market map and downloadable report.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--muted)] md:text-lg">
              Start an analysis run, stream progress in real time, inspect browser findings, and export PDF or JSON when the pipeline completes.
            </p>
          </div>
          <div className="rounded-[28px] border border-[var(--line)] bg-[rgba(255,255,255,0.52)] p-5">
            <div className="mb-3 text-sm text-[var(--muted)]">Pipeline stages</div>
            <div className="space-y-2 text-sm">
              <div>1. Find competitors</div>
              <div>2. Run live browser analysis</div>
              <div>3. Build structured competitor profiles</div>
              <div>4. Synthesize and export reports</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-[1.1fr_0.9fr]">
        <div className="panel rounded-[28px] p-6 md:p-8">
          <div className="mb-6">
            <p className="eyebrow mb-2">Start Analysis</p>
            <h2 className="text-2xl">Product input</h2>
          </div>

          <div className="grid gap-4">
            <label className="grid gap-2">
              <span className="text-sm text-[var(--muted)]">Product name</span>
              <input
                className="rounded-2xl border border-[var(--line)] bg-white px-4 py-3 outline-none"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                required
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm text-[var(--muted)]">Product description</span>
              <textarea
                className="min-h-28 rounded-2xl border border-[var(--line)] bg-white px-4 py-3 outline-none"
                value={productDescription}
                onChange={(e) => setProductDescription(e.target.value)}
                required
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm text-[var(--muted)]">Product URL</span>
              <input
                className="rounded-2xl border border-[var(--line)] bg-white px-4 py-3 outline-none"
                value={productUrl}
                onChange={(e) => setProductUrl(e.target.value)}
                placeholder="https://linear.app"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm text-[var(--muted)]">Differentiators</span>
              <textarea
                className="min-h-24 rounded-2xl border border-[var(--line)] bg-white px-4 py-3 outline-none"
                value={differentiators}
                onChange={(e) => setDifferentiators(e.target.value)}
                placeholder="Fast issue tracking, opinionated UX, built for software teams"
              />
            </label>
          </div>

          {error ? (
            <div className="mt-4 rounded-2xl border border-[#c76b52] bg-[#fff0ea] px-4 py-3 text-sm text-[#8b341d]">
              {error}
            </div>
          ) : null}

          <div className="mt-6 flex items-center gap-3">
            <button
              type="button"
              onClick={onSubmit}
              disabled={loading}
              className="rounded-full bg-[var(--brand)] px-6 py-3 text-sm text-white transition hover:bg-[var(--brand-deep)] disabled:opacity-60"
            >
              {loading ? "Starting..." : "Run Analysis"}
            </button>
            <span className="text-sm text-[var(--muted)]">You will be redirected to a live dashboard immediately.</span>
          </div>
        </div>

        <aside className="panel soft-grid rounded-[28px] p-6 md:p-8">
          <p className="eyebrow mb-2">What You Get</p>
          <h2 className="text-2xl">Live operational view</h2>
          <div className="mt-5 space-y-4 text-sm leading-7 text-[var(--muted)]">
            <p>The dashboard page streams browser progress, competitor analysis updates, synthesis output, and export links as soon as they are available.</p>
            <p>Late stream connections still work because your backend buffers prior events and replays them on connect.</p>
            <p>The final session page exposes PDF and JSON downloads directly from the backend export routes.</p>
          </div>
        </aside>
      </section>
    </main>
  );
}
