"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Download, FileJson } from "lucide-react";

type ExportBarProps = {
  exportUrls: { pdf_url: string | null; json_url: string | null } | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function absoluteUrl(url: string | null) {
  if (!url) {
    return "#";
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  return `${API_BASE}${url}`;
}

export function ExportBar({ exportUrls }: ExportBarProps) {
  if (!exportUrls) {
    return null;
  }

  const pdfUrl = absoluteUrl(exportUrls.pdf_url);
  const jsonUrl = absoluteUrl(exportUrls.json_url);

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 160, damping: 18 }}
      className="dashboard-panel"
    >
      <div className="panel-header">
        <div>
          <p className="eyebrow mb-1">Exports</p>
          <h2 className="panel-title">Reports ready</h2>
        </div>
      </div>

      <div className="mt-5 grid gap-3">
        <a href={pdfUrl} download className="export-button export-pdf">
          <Download className="h-4 w-4" />
          Download PDF Report
        </a>
        <a href={jsonUrl} download className="export-button export-json">
          <FileJson className="h-4 w-4" />
          Download JSON Data
        </a>
        <Link href="/" className="export-button export-secondary">
          Start New Research
        </Link>
      </div>
    </motion.section>
  );
}
