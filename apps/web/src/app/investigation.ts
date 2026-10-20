import type { CreateJobRequest, JobStatus } from "../api/types.js";

const JOB_KINDS = new Set(["search", "fetch", "browser"]);
const TERMINAL_STATUSES = new Set<JobStatus>(["succeeded", "failed", "cancelled"]);

function absoluteUrl(value: string, kind: "fetch" | "browser"): string {
  let url: URL;
  try {
    url = new URL(value.trim());
  } catch {
    throw new Error("Enter an absolute URL including https://.");
  }
  if (
    (kind === "browser" && url.protocol !== "https:")
    || (kind === "fetch" && !["http:", "https:"].includes(url.protocol))
    || url.username
    || url.password
    || (kind === "browser" && Boolean(url.port) && url.port !== "443")
  ) {
    throw new Error(kind === "browser"
      ? "Browser acquisition requires an HTTPS URL on port 443 without embedded credentials."
      : "Fetch requires an HTTP(S) URL without embedded credentials.");
  }
  return url.toString();
}

export function buildJobRequest(
  rawKind: string,
  rawQuestion: string,
  rawUrl: string,
  rawLimit: string,
): CreateJobRequest {
  if (!JOB_KINDS.has(rawKind)) throw new Error("Choose a supported acquisition method.");
  if (rawKind === "search") {
    const query = rawQuestion.trim();
    if (!query || query.length > 400) throw new Error("Search query must contain 1–400 characters.");
    const limit = Number(rawLimit);
    if (!Number.isInteger(limit) || ![5, 10, 20].includes(limit)) {
      throw new Error("Choose a supported result limit.");
    }
    return { kind: "search", payload: { query, limit } };
  }
  const url = absoluteUrl(rawUrl, rawKind as "fetch" | "browser");
  if (rawKind === "fetch") return { kind: "fetch", payload: { url } };
  return { kind: "browser", payload: { url } };
}

export function isTerminalJobStatus(status: JobStatus): boolean {
  return TERMINAL_STATUSES.has(status);
}
