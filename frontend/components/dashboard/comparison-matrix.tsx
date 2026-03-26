"use client";

import { Check } from "lucide-react";
import type { EventData } from "@/lib/sse";

type ComparisonMatrixProps = {
  synthesis: EventData | null;
};

function toMatrix(value: unknown) {
  return Array.isArray(value) ? (value as EventData[]) : [];
}

export function ComparisonMatrix({ synthesis }: ComparisonMatrixProps) {
  const matrix = toMatrix(synthesis?.matrix);
  const columns = matrix.length ? Object.keys(matrix[0]).filter((key) => key !== "feature") : [];

  return (
    <section className="dashboard-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow mb-1">Feature Matrix</p>
          <h2 className="panel-title">Capability comparison</h2>
        </div>
      </div>

      {matrix.length ? (
        <div className="mt-5 overflow-x-auto">
          <div
            className="matrix-grid"
            style={{ gridTemplateColumns: `minmax(240px, 1.5fr) repeat(${columns.length}, minmax(110px, 1fr))` }}
          >
            <div className="matrix-head">Feature</div>
            {columns.map((column) => (
              <div key={column} className={`matrix-head ${column === "us" ? "matrix-us-head" : ""}`}>
                {column === "us" ? "Our Product" : column}
              </div>
            ))}

            {matrix.map((row, rowIndex) => (
              <div className="contents" key={`${String(row.feature ?? "feature")}-${rowIndex}`}>
                <div className="matrix-feature">{String(row.feature ?? "Unnamed feature")}</div>
                {columns.map((column) => {
                  const value = Boolean(row[column]);
                  return (
                    <div key={`${rowIndex}-${column}`} className={`matrix-cell ${column === "us" ? "matrix-us-cell" : ""}`}>
                      {value ? <Check className="h-4 w-4 text-emerald-600" /> : <span className="text-slate-400">-</span>}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="mt-5 empty-note">The comparison matrix will render here after synthesis extracts feature coverage.</div>
      )}
    </section>
  );
}
