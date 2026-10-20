import { TwiApiClient } from "../api/client.js";
import { OAuthPkceTokenProvider } from "../api/oauth-pkce.js";

export interface TinlytRuntimeConfig {
  apiBaseUrl: string;
  apiAllowedOrigins?: string[];
  oauth: {
    issuer: string;
    authorizationEndpoint: string;
    tokenEndpoint: string;
    clientId: string;
    redirectUri: string;
    scope: string;
    resource: string;
    trustedIssuerOrigins: string[];
  };
}

export type TinlytRuntime =
  | { state: "not_configured"; message: string }
  | { state: "invalid_configuration"; message: string }
  | {
      state: "ready";
      apiClient: TwiApiClient;
      tokenProvider: OAuthPkceTokenProvider;
      beginLogin(): Promise<void>;
      handleCallback(callbackUrl?: string): Promise<void>;
      clearSession(): void;
    };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

export function createRuntime(config: unknown): TinlytRuntime {
  if (
    !isRecord(config)
    || typeof config.apiBaseUrl !== "string"
    || !config.apiBaseUrl
    || !isRecord(config.oauth)
    || typeof config.oauth.issuer !== "string"
    || !config.oauth.issuer
    || typeof config.oauth.authorizationEndpoint !== "string"
    || !config.oauth.authorizationEndpoint
    || typeof config.oauth.tokenEndpoint !== "string"
    || !config.oauth.tokenEndpoint
    || typeof config.oauth.clientId !== "string"
    || !config.oauth.clientId
    || typeof config.oauth.redirectUri !== "string"
    || !config.oauth.redirectUri
    || typeof config.oauth.scope !== "string"
    || !config.oauth.scope
    || typeof config.oauth.resource !== "string"
    || !config.oauth.resource
    || !isStringArray(config.oauth.trustedIssuerOrigins)
    || config.oauth.trustedIssuerOrigins.length < 1
    || (config.apiAllowedOrigins !== undefined && !isStringArray(config.apiAllowedOrigins))
  ) {
    return {
      state: "not_configured",
      message: "Platform identity and TWI API deployment configuration is not available.",
    };
  }

  try {
    const tokenProvider = new OAuthPkceTokenProvider({
      issuer: config.oauth.issuer,
      authorizationEndpoint: config.oauth.authorizationEndpoint,
      tokenEndpoint: config.oauth.tokenEndpoint,
      clientId: config.oauth.clientId,
      redirectUri: config.oauth.redirectUri,
      scope: config.oauth.scope,
      resource: config.oauth.resource,
      trustedIssuerOrigins: config.oauth.trustedIssuerOrigins,
    });
    const apiClient = new TwiApiClient({
      baseUrl: config.apiBaseUrl,
      allowedOrigins: config.apiAllowedOrigins ?? [],
      tokenProvider,
    });
    return {
      state: "ready",
      apiClient,
      tokenProvider,
      beginLogin: () => tokenProvider.beginLogin(),
      handleCallback: (callbackUrl) => tokenProvider.handleCallback(callbackUrl),
      clearSession: () => tokenProvider.clear(),
    };
  } catch {
    return {
      state: "invalid_configuration",
      message: "Platform identity configuration is invalid; sign-in is disabled.",
    };
  }
}

let runtimeSingleton: TinlytRuntime | null = null;

export function getRuntime(config: unknown): TinlytRuntime {
  runtimeSingleton ??= createRuntime(config);
  return runtimeSingleton;
}
