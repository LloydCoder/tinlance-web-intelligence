import { TwiApiError } from "./errors.js";
import type { AccessTokenProvider } from "./types.js";

const TRANSACTION_KEY = "tinlyt.oauth.pkce.transaction.v1";
const TRANSACTION_TTL_MS = 10 * 60 * 1000;
const TOKEN_REFRESH_SKEW_MS = 30_000;

interface PkceTransaction {
  state: string;
  verifier: string;
  createdAt: number;
}

export interface OAuthPkceConfig {
  authorizationEndpoint: string;
  tokenEndpoint: string;
  clientId: string;
  redirectUri: string;
  scope: string;
  resource: string;
  trustedIssuerOrigins: readonly string[];
  storage?: Pick<Storage, "getItem" | "setItem" | "removeItem">;
  cryptoImpl?: Crypto;
  fetchImpl?: typeof fetch;
  navigate?: (url: string) => void;
  replaceUrl?: (url: string) => void;
  now?: () => number;
  timeoutMs?: number;
}

/**
 * Public-client OAuth 2.0 Authorization Code + PKCE adapter.
 *
 * This adapter never embeds a client secret, never stores access/refresh tokens,
 * and accepts only explicitly trusted HTTPS authorization/token endpoints.
 * The resource server remains responsible for token signature, issuer, audience,
 * expiry, tenant, subject and delegated-scope validation.
 */
export class OAuthPkceTokenProvider implements AccessTokenProvider {
  private readonly authorizationEndpoint: URL;
  private readonly tokenEndpoint: URL;
  private readonly redirectUri: URL;
  private readonly clientId: string;
  private readonly scope: string;
  private readonly resource: string;
  private readonly storage: Pick<Storage, "getItem" | "setItem" | "removeItem">;
  private readonly cryptoImpl: Crypto;
  private readonly fetchImpl: typeof fetch;
  private readonly navigate: (url: string) => void;
  private readonly replaceUrl: (url: string) => void;
  private readonly now: () => number;
  private readonly timeoutMs: number;
  private accessToken: string | null = null;
  private expiresAt = 0;

  constructor(config: OAuthPkceConfig) {
    if (!config || !config.clientId || config.clientId !== config.clientId.trim()) {
      throw new TwiApiError("configuration_error", "A normalized public OAuth client ID is required.");
    }
    if (!config.scope || config.scope !== config.scope.trim() || /\s{2,}/.test(config.scope)) {
      throw new TwiApiError("configuration_error", "OAuth scopes must be explicitly configured and normalized.");
    }
    if (!config.resource || config.resource !== config.resource.trim()) {
      throw new TwiApiError("configuration_error", "The TWI API audience/resource is required.");
    }
    this.authorizationEndpoint = this.parseTrustedEndpoint(config.authorizationEndpoint, config.trustedIssuerOrigins);
    this.tokenEndpoint = this.parseTrustedEndpoint(config.tokenEndpoint, config.trustedIssuerOrigins);
    this.redirectUri = this.parseRedirectUri(config.redirectUri);
    this.clientId = config.clientId;
    this.scope = config.scope;
    this.resource = config.resource;
    this.storage = config.storage ?? this.browserStorage();
    this.cryptoImpl = config.cryptoImpl ?? globalThis.crypto;
    this.fetchImpl = config.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.navigate = config.navigate ?? ((url) => {
      if (typeof window === "undefined") throw new TwiApiError("configuration_error", "Browser navigation is unavailable.");
      window.location.assign(url);
    });
    this.replaceUrl = config.replaceUrl ?? ((url) => {
      if (typeof window !== "undefined") window.history.replaceState(null, "", url);
    });
    this.now = config.now ?? Date.now;
    this.timeoutMs = config.timeoutMs ?? 10_000;
    if (!Number.isInteger(this.timeoutMs) || this.timeoutMs < 1000 || this.timeoutMs > 30_000) {
      throw new TwiApiError("configuration_error", "The identity token endpoint timeout must be between 1000 and 30000 milliseconds.");
    }
    if (!this.cryptoImpl?.subtle || !this.cryptoImpl.getRandomValues) {
      throw new TwiApiError("configuration_error", "Web Crypto with SHA-256 is required for PKCE.");
    }
  }

  async beginLogin(): Promise<void> {
    const state = this.randomBase64Url(32);
    const verifier = this.randomBase64Url(48);
    const challenge = await this.sha256Base64Url(verifier);
    const transaction: PkceTransaction = { state, verifier, createdAt: this.now() };
    this.storage.setItem(TRANSACTION_KEY, JSON.stringify(transaction));

    const authorization = new URL(this.authorizationEndpoint);
    authorization.searchParams.set("response_type", "code");
    authorization.searchParams.set("client_id", this.clientId);
    authorization.searchParams.set("redirect_uri", this.redirectUri.toString());
    authorization.searchParams.set("scope", this.scope);
    authorization.searchParams.set("state", state);
    authorization.searchParams.set("code_challenge", challenge);
    authorization.searchParams.set("code_challenge_method", "S256");
    authorization.searchParams.set("resource", this.resource);
    this.navigate(authorization.toString());
  }

  async handleCallback(callbackUrl?: string): Promise<void> {
    const url = new URL(callbackUrl ?? this.currentUrl());
    if (url.origin !== this.redirectUri.origin || url.pathname !== this.redirectUri.pathname) {
      throw new TwiApiError("authentication_required", "The OAuth callback URL does not match the configured redirect URI.");
    }
    this.accessToken = null;
    this.expiresAt = 0;
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const oauthError = url.searchParams.get("error");
    const transaction = this.readTransaction();

    // Remove one-time OAuth parameters from the visible URL before exchanging the code.
    url.searchParams.delete("code");
    url.searchParams.delete("state");
    url.searchParams.delete("error");
    url.searchParams.delete("error_description");
    this.replaceUrl(url.toString());

    this.storage.removeItem(TRANSACTION_KEY);
    if (oauthError) {
      throw new TwiApiError("authentication_required", "The identity provider rejected authorization.");
    }
    if (!code || code.length > 4096 || !state || state.length > 256 || !transaction || state !== transaction.state) {
      throw new TwiApiError("authentication_required", "The OAuth callback state is missing or invalid.");
    }
    if (this.now() - transaction.createdAt > TRANSACTION_TTL_MS || this.now() < transaction.createdAt) {
      throw new TwiApiError("authentication_required", "The OAuth authorization transaction expired.");
    }

    const body = new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: this.redirectUri.toString(),
      client_id: this.clientId,
      code_verifier: transaction.verifier,
      resource: this.resource,
    });

    let response: Response;
    let tokenResponse: unknown;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      response = await this.fetchImpl(this.tokenEndpoint, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: body.toString(),
        signal: controller.signal,
        redirect: "error",
        credentials: "omit",
        cache: "no-store",
      });
      if (!response.ok) {
        throw new TwiApiError("authentication_required", "The identity provider could not issue a TWI access token.", response.status);
      }
      try {
        tokenResponse = await response.json() as unknown;
      } catch {
        if (controller.signal.aborted) {
          throw new TwiApiError("request_timeout", "The identity token endpoint timed out.");
        }
        throw new TwiApiError("invalid_response", "The identity provider returned malformed token data.", response.status);
      }
    } catch (error) {
      if (error instanceof TwiApiError) throw error;
      if (controller.signal.aborted) {
        throw new TwiApiError("request_timeout", "The identity token endpoint timed out.");
      }
      throw new TwiApiError("network_error", "The identity token endpoint could not be reached.");
    } finally {
      globalThis.clearTimeout(timeout);
    }
    if (
      !this.isRecord(tokenResponse)
      || typeof tokenResponse.access_token !== "string"
      || !tokenResponse.access_token
      || tokenResponse.access_token.length > 16_384
      || /\s/.test(tokenResponse.access_token)
      || typeof tokenResponse.token_type !== "string"
      || tokenResponse.token_type.toLowerCase() !== "bearer"
      || typeof tokenResponse.expires_in !== "number"
      || !Number.isInteger(tokenResponse.expires_in)
      || tokenResponse.expires_in <= TOKEN_REFRESH_SKEW_MS / 1000
      || tokenResponse.expires_in > 86_400
    ) {
      throw new TwiApiError("invalid_response", "The identity provider returned an unsupported token response.");
    }
    // Access token stays in memory only. Refresh tokens are deliberately ignored.
    this.accessToken = tokenResponse.access_token;
    this.expiresAt = this.now() + tokenResponse.expires_in * 1000;
  }

  async getAccessToken(): Promise<string> {
    if (!this.accessToken || this.expiresAt - this.now() <= TOKEN_REFRESH_SKEW_MS) {
      this.accessToken = null;
      this.expiresAt = 0;
      throw new TwiApiError("authentication_required", "A valid in-memory TWI access token is unavailable; sign in again.");
    }
    return this.accessToken;
  }

  clear(): void {
    this.accessToken = null;
    this.expiresAt = 0;
    this.storage.removeItem(TRANSACTION_KEY);
  }

  private parseTrustedEndpoint(value: string, trustedOrigins: readonly string[]): URL {
    let url: URL;
    try { url = new URL(value); } catch {
      throw new TwiApiError("configuration_error", "OAuth endpoints must be absolute URLs.");
    }
    if (
      url.protocol !== "https:"
      || !url.hostname
      || url.username
      || url.password
      || url.hash
      || !trustedOrigins.some((origin) => {
        try {
          const parsed = new URL(origin);
          return parsed.protocol === "https:" && parsed.origin === url.origin;
        } catch {
          return false;
        }
      })
    ) {
      throw new TwiApiError("configuration_error", "OAuth endpoints must use an explicitly trusted HTTPS origin.");
    }
    return url;
  }

  private parseRedirectUri(value: string): URL {
    let url: URL;
    try { url = new URL(value); } catch {
      throw new TwiApiError("configuration_error", "The OAuth redirect URI must be absolute.");
    }
    const localDevelopment = url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
    if (
      (url.protocol !== "https:" && !localDevelopment)
      || url.username
      || url.password
      || url.search
      || url.hash
    ) {
      throw new TwiApiError("configuration_error", "The OAuth redirect URI must be HTTPS and must not contain credentials, query, or fragment data.");
    }
    return url;
  }

  private readTransaction(): PkceTransaction | null {
    const raw = this.storage.getItem(TRANSACTION_KEY);
    if (!raw) return null;
    try {
      const value: unknown = JSON.parse(raw);
      if (
        !this.isRecord(value)
        || typeof value.state !== "string"
        || typeof value.verifier !== "string"
        || typeof value.createdAt !== "number"
      || !Number.isFinite(value.createdAt)
      || !/^[A-Za-z0-9_-]{43}$/.test(value.state)
      || !/^[A-Za-z0-9_-]{64}$/.test(value.verifier)
      ) return null;
      return { state: value.state, verifier: value.verifier, createdAt: value.createdAt };
    } catch {
      return null;
    }
  }

  private randomBase64Url(size: number): string {
    const bytes = this.cryptoImpl.getRandomValues(new Uint8Array(size));
    return this.toBase64Url(bytes);
  }

  private async sha256Base64Url(value: string): Promise<string> {
    const digest = await this.cryptoImpl.subtle.digest("SHA-256", new TextEncoder().encode(value));
    return this.toBase64Url(new Uint8Array(digest));
  }

  private toBase64Url(bytes: Uint8Array): string {
    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  private currentUrl(): string {
    if (typeof window === "undefined") {
      throw new TwiApiError("configuration_error", "Browser callback URL is unavailable.");
    }
    return window.location.href;
  }

  private browserStorage(): Pick<Storage, "getItem" | "setItem" | "removeItem"> {
    if (typeof window === "undefined") {
      throw new TwiApiError("configuration_error", "Session storage must be injected outside a browser.");
    }
    return window.sessionStorage;
  }

  private isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }
}
