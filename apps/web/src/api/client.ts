import { errorForStatus, TwiApiError } from "./errors.js";
import { readBoundedJson } from "./json.js";
import type {
  CreateJobRequest,
  EvidencePackage,
  Job,
  JobKind,
  JobStatus,
  TwiApiClientOptions,
  VerifyResearchRequest,
  VerifyResearchResponse,
} from "./types.js";

const JOB_KINDS = new Set<JobKind>(["search", "fetch", "browser"]);
const JOB_STATUSES = new Set<JobStatus>(["queued", "running", "succeeded", "failed", "cancelled"]);
const DEFAULT_TIMEOUT_MS = 15_000;
const MAX_API_RESPONSE_BYTES = 30_000_000;
const MIN_IDEMPOTENCY_KEY_LENGTH = 16;
const MAX_IDEMPOTENCY_KEY_LENGTH = 256;

function normalizedBaseUrl(value: string, allowedOrigins: readonly string[] = []): string {
  if (!value || value !== value.trim()) {
    throw new TwiApiError("configuration_error", "A normalized API base URL is required.");
  }
  let url: URL;
  try {
    url = new URL(value, typeof window === "undefined" ? "https://tinlyt.invalid" : window.location.origin);
  } catch {
    throw new TwiApiError("configuration_error", "The API base URL is invalid.");
  }
  const origin = typeof window === "undefined" ? "https://tinlyt.invalid" : window.location.origin;
  const localDevelopment = url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  const sameOrigin = url.origin === origin;
  const explicitlyAllowed = allowedOrigins.some((candidate) => {
    try {
      const approved = new URL(candidate);
      return approved.protocol === "https:" && approved.origin === url.origin;
    } catch {
      return false;
    }
  });
  if (url.protocol !== "https:" && !localDevelopment) {
    throw new TwiApiError("configuration_error", "The API must use HTTPS outside localhost development.");
  }
  if (!sameOrigin && !localDevelopment && !explicitlyAllowed) {
    throw new TwiApiError("configuration_error", "Cross-origin API requests require an explicit HTTPS origin allowlist.");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new TwiApiError("configuration_error", "The API base URL must not contain credentials, query parameters, or fragments.");
  }
  url.pathname = url.pathname.replace(/\/+$/, "");
  return url.toString().replace(/\/$/, "");
}

function validIdempotencyKey(value: string): string {
  if (
    value.length < MIN_IDEMPOTENCY_KEY_LENGTH
    || value.length > MAX_IDEMPOTENCY_KEY_LENGTH
    || !/^[\x21-\x7e]+$/.test(value)
  ) {
    throw new TwiApiError("configuration_error", "The idempotency key is invalid.");
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseJob(value: unknown): Job {
  if (!isRecord(value)) {
    throw new TwiApiError("invalid_response", "The API returned an invalid job response.");
  }
  if (
    typeof value.job_id !== "string"
    || typeof value.kind !== "string"
    || !JOB_KINDS.has(value.kind as JobKind)
    || typeof value.status !== "string"
    || !JOB_STATUSES.has(value.status as JobStatus)
    || typeof value.created_at !== "string"
    || typeof value.updated_at !== "string"
    || typeof value.attempts !== "number"
    || typeof value.max_attempts !== "number"
    || typeof value.cancel_requested !== "boolean"
    || !(value.result === null || isRecord(value.result))
    || !(value.error_code === null || typeof value.error_code === "string")
    || !isRecord(value.payload)
  ) {
    throw new TwiApiError("invalid_response", "The API returned a job that does not match the supported contract.");
  }
  return {
    job_id: value.job_id,
    kind: value.kind as JobKind,
    payload: value.payload,
    status: value.status as JobStatus,
    created_at: value.created_at,
    updated_at: value.updated_at,
    attempts: value.attempts,
    max_attempts: value.max_attempts,
    result: value.result,
    error_code: value.error_code,
    cancel_requested: value.cancel_requested,
  };
}

function parseEvidencePackage(value: unknown): EvidencePackage {
  if (
    !isRecord(value)
    || value.format !== "application/vnd.tinlance.twi-evidence+json"
    || value.schema_version !== "1.0.0"
    || typeof value.content_base64 !== "string"
    || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value.content_base64)
    || typeof value.content_type !== "string"
    || !value.content_type
    || typeof value.content_sha256 !== "string"
    || !/^[0-9a-f]{64}$/.test(value.content_sha256)
    || typeof value.export_id !== "string"
    || !/^sha256:[0-9a-f]{64}$/.test(value.export_id)
    || typeof value.artifact_id !== "string"
    || value.artifact_id !== `sha256:${value.content_sha256}`
    || typeof value.byte_size !== "number"
    || !Number.isInteger(value.byte_size)
    || value.byte_size < 0
    || value.byte_size > 20_000_000
    || !isRecord(value.provenance)
    || value.provenance.schema_version !== "1.0.0"
    || typeof value.provenance.requested_url_sha256 !== "string"
    || !/^[0-9a-f]{64}$/.test(value.provenance.requested_url_sha256)
    || typeof value.provenance.final_url_sha256 !== "string"
    || !/^[0-9a-f]{64}$/.test(value.provenance.final_url_sha256)
    || typeof value.provenance.status_code !== "number"
    || !Number.isInteger(value.provenance.status_code)
    || value.provenance.status_code < 200
    || value.provenance.status_code > 599
    || value.provenance.content_type !== value.content_type
    || value.provenance.content_sha256 !== value.content_sha256
    || value.provenance.byte_size !== value.byte_size
    || typeof value.provenance.retrieved_at !== "string"
    || !Number.isFinite(Date.parse(value.provenance.retrieved_at))
    || typeof value.provenance.redirect_count !== "number"
    || !Number.isInteger(value.provenance.redirect_count)
    || value.provenance.redirect_count < 0
    || value.provenance.redirect_count > 100
    || typeof value.provenance.extractor_version !== "string"
    || !value.provenance.extractor_version
    || value.provenance.extractor_version.length > 64
    || typeof value.source_revision !== "string"
    || !/^[0-9a-f]{40}$/.test(value.source_revision)
    || !isRecord(value.interpretation)
    || value.interpretation.provenance_kind !== "acquisition_observation"
    || value.interpretation.truth_assessment !== "not_provided"
    || value.interpretation.source_authority_assessment !== "not_provided"
  ) {
    throw new TwiApiError("invalid_response", "The evidence package does not match the supported contract.");
  }
  return value as unknown as EvidencePackage;
}

function validateCreateRequest(request: CreateJobRequest): void {
  if (!request || !JOB_KINDS.has(request.kind) || !isRecord(request.payload)) {
    throw new TwiApiError("validation_error", "The job request is invalid.");
  }
  if (request.kind === "search") {
    const payload = request.payload;
    if (
      typeof payload.query !== "string"
      || payload.query.trim().length < 1
      || payload.query.length > 400
      || (payload.limit !== undefined && (typeof payload.limit !== "number" || !Number.isInteger(payload.limit) || payload.limit < 1 || payload.limit > 20))
      || Object.keys(payload).some((key) => !["query", "limit"].includes(key))
    ) {
      throw new TwiApiError("validation_error", "The search request does not match the supported contract.");
    }
  } else if (request.kind === "fetch") {
    const payload = request.payload;
    if (
      typeof payload.url !== "string"
      || Object.keys(payload).some((key) => key !== "url")
    ) {
      throw new TwiApiError("validation_error", "The fetch request does not match the supported contract.");
    }
    let url: URL;
    try { url = new URL(payload.url); } catch {
      throw new TwiApiError("validation_error", "The fetch URL must be absolute.");
    }
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) {
      throw new TwiApiError("validation_error", "The fetch URL scheme or authority is not supported.");
    }
  } else {
    const payload = request.payload;
    if (
      typeof payload.url !== "string"
      || (payload.wait_until !== undefined && !["domcontentloaded", "load"].includes(String(payload.wait_until)))
      || (payload.timeout_ms !== undefined && (typeof payload.timeout_ms !== "number" || !Number.isInteger(payload.timeout_ms) || payload.timeout_ms < 1000 || payload.timeout_ms > 30000))
      || (payload.include_screenshot !== undefined && typeof payload.include_screenshot !== "boolean")
      || Object.keys(payload).some((key) => !["url", "wait_until", "timeout_ms", "include_screenshot"].includes(key))
    ) {
      throw new TwiApiError("validation_error", "The browser request does not match the supported contract.");
    }
    let url: URL;
    try { url = new URL(payload.url); } catch {
      throw new TwiApiError("validation_error", "The browser URL must be absolute.");
    }
    if (url.protocol !== "https:" || url.port && url.port !== "443" || url.username || url.password) {
      throw new TwiApiError("validation_error", "Browser acquisition requires an HTTPS URL on port 443.");
    }
  }
}

export class TwiApiClient {
  private readonly baseUrl: string;
  private readonly tokenProvider: TwiApiClientOptions["tokenProvider"];
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;
  private readonly idempotencyKeyFactory: () => string;

  constructor(options: TwiApiClientOptions) {
    if (!options || !options.tokenProvider || typeof options.tokenProvider.getAccessToken !== "function") {
      throw new TwiApiError("configuration_error", "An approved Platform access-token provider must be injected.");
    }
    this.baseUrl = normalizedBaseUrl(options.baseUrl, options.allowedOrigins);
    this.tokenProvider = options.tokenProvider;
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.idempotencyKeyFactory = options.idempotencyKeyFactory ?? (() => globalThis.crypto.randomUUID());
    if (!Number.isInteger(this.timeoutMs) || this.timeoutMs < 1000 || this.timeoutMs > 60000) {
      throw new TwiApiError("configuration_error", "The API timeout must be between 1000 and 60000 milliseconds.");
    }
  }

  async createJob(request: CreateJobRequest, idempotencyKey?: string): Promise<Job> {
    validateCreateRequest(request);
    const key = validIdempotencyKey(idempotencyKey ?? this.idempotencyKeyFactory());
    return parseJob(await this.request("/v1/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": key },
      body: JSON.stringify(request),
    }));
  }

  async getJob(jobId: string): Promise<Job> {
    return parseJob(await this.request(`/v1/jobs/${encodeURIComponent(this.validateId(jobId))}`, { method: "GET" }));
  }

  async cancelJob(jobId: string): Promise<Job> {
    return parseJob(await this.request(`/v1/jobs/${encodeURIComponent(this.validateId(jobId))}/cancel`, { method: "POST" }));
  }

  async exportEvidence(jobId: string): Promise<EvidencePackage> {
    const value = await this.request(`/v1/jobs/${encodeURIComponent(this.validateId(jobId))}/evidence`, { method: "GET" });
    return parseEvidencePackage(value);
  }

  async verifyResearch(request: VerifyResearchRequest): Promise<VerifyResearchResponse> {
    if (!request || !Array.isArray(request.claims) || request.claims.length < 1 || request.claims.length > 20) {
      throw new TwiApiError("validation_error", "The verification request must contain between 1 and 20 claims.");
    }
    const ids = new Set<string>();
    for (const claim of request.claims) {
      if (
        !claim
        || typeof claim.claim_id !== "string"
        || !/^[A-Za-z0-9._:-]{1,64}$/.test(claim.claim_id)
        || ids.has(claim.claim_id)
        || typeof claim.statement !== "string"
        || claim.statement.trim().length < 1
        || claim.statement.length > 500
        || !Array.isArray(claim.citations)
        || claim.citations.length < 1
        || claim.citations.length > 4
      ) {
        throw new TwiApiError("validation_error", "A claim does not match the supported verification contract.");
      }
      ids.add(claim.claim_id);
      for (const citation of claim.citations) {
        if (
          !citation
          || !this.isValidJobId(citation.job_id)
          || typeof citation.quote !== "string"
          || citation.quote.length < 8
          || citation.quote.length > 350
        ) {
          throw new TwiApiError("validation_error", "A citation does not match the supported verification contract.");
        }
      }
    }
    return this.parseVerificationResponse(await this.request("/v1/research/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }));
  }

  private parseVerificationResponse(value: unknown): VerifyResearchResponse {
    if (
      !isRecord(value)
      || typeof value.verification_id !== "string"
      || !value.verification_id
      || typeof value.verifier_version !== "string"
      || !value.verifier_version
      || typeof value.verified_at !== "string"
      || !Number.isFinite(Date.parse(value.verified_at))
      || typeof value.report_sha256 !== "string"
      || !/^[0-9a-f]{64}$/.test(value.report_sha256)
      || !["all_citations_match_captured_text", "citation_mismatch"].includes(String(value.status))
      || value.factual_truth_assessed !== false
      || !Array.isArray(value.claims)
      || value.claims.length < 1
      || value.claims.length > 20
    ) {
      throw new TwiApiError("invalid_response", "The API returned an invalid verification response.");
    }
    const claimsValid = value.claims.every((claim) => {
      if (
        !isRecord(claim)
        || typeof claim.claim_id !== "string"
        || !/^[A-Za-z0-9._:-]{1,64}$/.test(claim.claim_id)
        || typeof claim.statement !== "string"
        || !claim.statement.trim()
        || !["all_citations_match_captured_text", "citation_mismatch", "partially_matched_citations"].includes(String(claim.citation_status))
        || !Array.isArray(claim.citations)
        || claim.citations.length < 1
        || claim.citations.length > 4
      ) return false;
      let matchedCount = 0;
      const citationsValid = claim.citations.every((citation) => {
        if (
          !isRecord(citation)
          || typeof citation.job_id !== "string"
          || !this.isValidJobId(citation.job_id)
          || typeof citation.quote !== "string"
          || citation.quote.length < 8
          || citation.quote.length > 350
          || typeof citation.quote_match !== "boolean"
          || citation.match_status !== (citation.quote_match ? "matched" : "quote_not_found")
          || !isRecord(citation.source)
          || typeof citation.source.url !== "string"
          || typeof citation.source.retrieved_at !== "string"
          || !Number.isFinite(Date.parse(citation.source.retrieved_at))
          || typeof citation.source.media_type !== "string"
          || !citation.source.media_type
          || typeof citation.source.content_sha256 !== "string"
          || !/^[0-9a-f]{64}$/.test(citation.source.content_sha256)
        ) return false;
        if (citation.quote_match) matchedCount += 1;
        try {
          const sourceUrl = new URL(citation.source.url);
          return ["http:", "https:"].includes(sourceUrl.protocol) && !sourceUrl.username && !sourceUrl.password;
        } catch {
          return false;
        }
      });
      if (!citationsValid) return false;
      const expectedStatus = matchedCount === claim.citations.length
        ? "all_citations_match_captured_text"
        : matchedCount === 0
          ? "citation_mismatch"
          : "partially_matched_citations";
      return claim.citation_status === expectedStatus;
    });
    if (!claimsValid) {
      throw new TwiApiError("invalid_response", "The API returned malformed claim or citation evidence.");
    }
    const allMatched = value.claims.every((claim) => isRecord(claim) && claim.citation_status === "all_citations_match_captured_text");
    if ((value.status === "all_citations_match_captured_text") !== allMatched) {
      throw new TwiApiError("invalid_response", "The verification status conflicts with its citation results.");
    }
    return value as unknown as VerifyResearchResponse;
  }

  private isValidJobId(value: string): boolean {
    return typeof value === "string" && value.length > 0 && value.length <= 64 && /^[A-Za-z0-9._:-]+$/.test(value);
  }

  private validateId(value: string): string {
    if (!value || value.length > 64 || !/^[A-Za-z0-9._:-]+$/.test(value)) {
      throw new TwiApiError("validation_error", "The resource identifier is invalid.");
    }
    return value;
  }

  private async request(path: string, init: RequestInit): Promise<unknown> {
    let token: string;
    try {
      token = await this.tokenProvider.getAccessToken();
    } catch {
      throw new TwiApiError("authentication_required", "The approved Platform identity provider could not supply an access token.");
    }
    if (!token || token !== token.trim() || /\s/.test(token)) {
      throw new TwiApiError("authentication_required", "The approved Platform identity provider returned an invalid access token.");
    }

    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchImpl(new URL(path.replace(/^\//, ""), `${this.baseUrl.replace(/\/$/, "")}/`), {
        ...init,
        headers: {
          Accept: "application/json",
          ...init.headers,
          Authorization: `Bearer ${token}`,
        },
        signal: controller.signal,
        redirect: "error",
        credentials: "omit",
        cache: "no-store",
      });
      const requestId = response.headers.get("x-request-id");
      if (!response.ok) throw errorForStatus(response.status, requestId);
      if (response.status === 204) return null;
      const contentType = response.headers.get("content-type") ?? "";
      if (!contentType.toLowerCase().includes("application/json") && !contentType.toLowerCase().includes("application/vnd.tinlance.twi-evidence+json")) {
        throw new TwiApiError("invalid_response", "The API returned an unsupported response media type.", response.status, requestId);
      }
      return await readBoundedJson(response, MAX_API_RESPONSE_BYTES, "The API response", controller.signal);
    } catch (error) {
      if (error instanceof TwiApiError) throw error;
      if (controller.signal.aborted) {
        throw new TwiApiError("request_timeout", "The API request timed out.");
      }
      throw new TwiApiError("network_error", "The API request could not be completed.");
    } finally {
      globalThis.clearTimeout(timeout);
    }
  }
}
