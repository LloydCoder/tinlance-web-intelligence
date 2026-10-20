import { TwiApiError } from "./errors.js";

export async function readBoundedJson(response: Response, maximumBytes: number, label: string, signal?: AbortSignal): Promise<unknown> {
  const declaredLength = response.headers.get("content-length");
  if (declaredLength && /^\d+$/.test(declaredLength) && Number(declaredLength) > maximumBytes) {
    throw new TwiApiError("invalid_response", `${label} exceeded the response size limit.`, response.status, response.headers.get("x-request-id"));
  }
  if (!response.body) {
    throw new TwiApiError("invalid_response", `${label} returned an empty JSON body.`, response.status, response.headers.get("x-request-id"));
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      total += part.value.byteLength;
      if (total > maximumBytes) {
        await reader.cancel();
        throw new TwiApiError("invalid_response", `${label} exceeded the response size limit.`, response.status, response.headers.get("x-request-id"));
      }
      chunks.push(part.value);
    }
  } catch (error) {
    if (error instanceof TwiApiError) throw error;
    if (signal?.aborted) throw new TwiApiError("request_timeout", `${label} timed out.`, response.status, response.headers.get("x-request-id"));
    throw new TwiApiError("network_error", `${label} could not be read completely.`, response.status, response.headers.get("x-request-id"));
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) as unknown;
  } catch {
    throw new TwiApiError("invalid_response", `${label} returned malformed JSON.`, response.status, response.headers.get("x-request-id"));
  }
}
