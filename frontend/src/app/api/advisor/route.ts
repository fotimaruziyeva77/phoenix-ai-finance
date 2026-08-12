import { NextResponse } from "next/server";

/**
 * Gemini bridge for the advisor chat.
 *
 * The deterministic engine computes every figure client-side; this route only
 * asks Gemini to *phrase a short explanation* of numbers it is handed. The key
 * lives in server env (`frontend/.env.local`), never in the browser bundle.
 *
 * Without a key the route answers `{ available: false }` and the chat silently
 * stays rule-based — the demo never depends on network or quota.
 */

const GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models";
// "-latest" alias keeps working as Google retires dated model ids.
const DEFAULT_MODEL = "gemini-flash-latest";
const TIMEOUT_MS = 20_000;
const MAX_SUMMARY_CHARS = 4_000;

const LANG_NAME: Record<string, string> = {
  uz: "Uzbek (Latin script)",
  ru: "Russian",
  en: "English",
};

function systemInstruction(lang: string): string {
  const language = LANG_NAME[lang] ?? LANG_NAME.uz;
  return [
    "You are the Phoenix AI financial advisor for small entrepreneurs in Uzbekistan.",
    "You receive figures that were ALREADY COMPUTED by a deterministic calculator.",
    "Explain what they mean for the entrepreneur in plain, warm language.",
    "STRICT RULES:",
    "- Never change, recompute, or invent any number. Quote them exactly as given.",
    "- Maximum 120 words. No headings, no lists, no markdown.",
    "- No guarantees or promises; this is planning information, not licensed advice.",
    "- End with one short sentence advising to confirm with an accountant or bank.",
    `- Answer strictly in ${language}.`,
  ].join("\n");
}

export async function POST(request: Request) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ available: false });
  }

  let body: { summary?: unknown; lang?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ available: false, error: "bad_request" }, { status: 400 });
  }

  const summary = typeof body.summary === "string" ? body.summary.trim() : "";
  const lang = typeof body.lang === "string" ? body.lang : "uz";
  if (!summary) {
    return NextResponse.json({ available: false, error: "empty_summary" }, { status: 400 });
  }

  const model = process.env.GEMINI_MODEL || DEFAULT_MODEL;

  const payload = JSON.stringify({
    system_instruction: { parts: [{ text: systemInstruction(lang) }] },
    contents: [{ role: "user", parts: [{ text: summary.slice(0, MAX_SUMMARY_CHARS) }] }],
    // NOTE: no thinkingConfig — the "-latest" alias currently rejects
    // thinkingBudget with a 400. The budget below leaves room for the
    // model's internal thinking tokens plus the ~120-word reply.
    generationConfig: { temperature: 0.3, maxOutputTokens: 900 },
  });

  // 429/503 are routine "model busy" blips — one short-backoff retry clears most.
  let lastError = "unreachable";
  for (let attempt = 0; attempt < 3; attempt += 1) {
    if (attempt > 0) await new Promise((resolve) => setTimeout(resolve, 1200 * attempt));
    try {
      const res = await fetch(`${GEMINI_ENDPOINT}/${model}:generateContent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey,
        },
        body: payload,
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });

      if (res.status === 429 || res.status === 503) {
        lastError = `gemini_${res.status}`;
        continue;
      }
      if (!res.ok) {
        return NextResponse.json({ available: false, error: `gemini_${res.status}` });
      }

      const data = (await res.json()) as {
        candidates?: {
          content?: { parts?: { text?: string; thought?: boolean }[] };
        }[];
      };
      // Gemini 3 models interleave reasoning parts (`thought: true`) with the
      // answer; only the answer parts belong to the user.
      const text = data.candidates?.[0]?.content?.parts
        ?.filter((p) => !p.thought)
        .map((p) => p.text ?? "")
        .join("")
        .trim();

      if (!text) {
        lastError = "empty_response";
        continue;
      }
      return NextResponse.json({ available: true, text });
    } catch {
      lastError = "unreachable";
    }
  }
  // Every attempt failed — the rule-based results keep working without us.
  return NextResponse.json({ available: false, error: lastError });
}
