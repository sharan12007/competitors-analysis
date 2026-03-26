export type AnalyzePayload = {
  product_name: string;
  product_description: string;
  product_url?: string;
  differentiators?: string;
};

export type AnalyzeResponse = {
  session_id: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function startAnalysis(payload: AnalyzePayload): Promise<string> {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Analyze request failed with status ${response.status}`);
  }

  const body = (await response.json()) as AnalyzeResponse;
  return body.session_id;
}

export function getExportUrls(sessionId: string) {
  return {
    pdf_url: `${API_BASE}/export/${sessionId}/pdf`,
    json_url: `${API_BASE}/export/${sessionId}/json`,
  };
}
