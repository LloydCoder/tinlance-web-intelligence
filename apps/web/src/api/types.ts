export type JobKind = "search" | "fetch" | "browser";
export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type BrowserWaitUntil = "domcontentloaded" | "load";

export interface SearchPayload {
  query: string;
  limit?: number;
}

export interface FetchPayload {
  url: string;
}

export interface BrowserPayload {
  url: string;
  wait_until?: BrowserWaitUntil;
  timeout_ms?: number;
  include_screenshot?: boolean;
}

export type JobPayloadByKind = {
  search: SearchPayload;
  fetch: FetchPayload;
  browser: BrowserPayload;
};

export type CreateJobRequest =
  | { kind: "search"; payload: SearchPayload }
  | { kind: "fetch"; payload: FetchPayload }
  | { kind: "browser"; payload: BrowserPayload };

export interface Job {
  job_id: string;
  kind: JobKind;
  payload: Record<string, unknown>;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  attempts: number;
  max_attempts: number;
  result: Record<string, unknown> | null;
  error_code: string | null;
  cancel_requested: boolean;
}

export interface EvidencePackage {
  format: "application/vnd.tinlance.twi-evidence+json";
  schema_version: "1.0.0";
  export_id: string;
  artifact_id: string;
  content_sha256: string;
  content_type: string;
  byte_size: number;
  source_revision: string;
  provenance: Record<string, unknown>;
  content_base64: string;
  interpretation: {
    provenance_kind: "acquisition_observation";
    truth_assessment: "not_provided";
    source_authority_assessment: "not_provided";
  };
}

export interface CitationRequest {
  job_id: string;
  quote: string;
}

export interface ClaimRequest {
  claim_id: string;
  statement: string;
  citations: CitationRequest[];
}

export interface VerifyResearchRequest {
  claims: ClaimRequest[];
}

export interface VerifyResearchResponse {
  [key: string]: unknown;
}

export interface AccessTokenProvider {
  /**
   * Returns a short-lived, audience-bound Platform access token for the TWI API.
   * Implementations must not persist tokens in localStorage, URLs, logs, or analytics.
   */
  getAccessToken(): Promise<string>;
}

export interface TwiApiClientOptions {
  /** HTTPS TWI API origin or a same-origin reverse-proxy base path. */
  baseUrl: string;
  tokenProvider: AccessTokenProvider;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
  /** Additional HTTPS API origins explicitly approved by deployment configuration. */
  allowedOrigins?: readonly string[];
  idempotencyKeyFactory?: () => string;
}
