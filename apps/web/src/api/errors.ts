export type TwiApiErrorCode =
  | "configuration_error"
  | "authentication_required"
  | "permission_denied"
  | "not_found"
  | "conflict"
  | "validation_error"
  | "rate_limited"
  | "request_timeout"
  | "network_error"
  | "server_error"
  | "invalid_response"
  | "http_error";

export class TwiApiError extends Error {
  readonly code: TwiApiErrorCode;
  readonly status: number | null;
  readonly requestId: string | null;

  constructor(
    code: TwiApiErrorCode,
    message: string,
    status: number | null = null,
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "TwiApiError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

export function errorForStatus(status: number, requestId: string | null): TwiApiError {
  if (status === 401) {
    return new TwiApiError("authentication_required", "Authentication is required.", status, requestId);
  }
  if (status === 403) {
    return new TwiApiError("permission_denied", "The current identity lacks the required permission.", status, requestId);
  }
  if (status === 404) {
    return new TwiApiError("not_found", "The requested resource was not found.", status, requestId);
  }
  if (status === 409) {
    return new TwiApiError("conflict", "The operation conflicts with the current resource state.", status, requestId);
  }
  if (status === 422) {
    return new TwiApiError("validation_error", "The request was rejected by the API contract.", status, requestId);
  }
  if (status === 429) {
    return new TwiApiError("rate_limited", "The service rate limit was reached.", status, requestId);
  }
  if (status >= 500) {
    return new TwiApiError("server_error", "The service could not complete the request.", status, requestId);
  }
  return new TwiApiError("http_error", "The API request failed.", status, requestId);
}
