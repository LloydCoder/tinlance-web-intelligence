// Public, non-secret deployment settings. Replace these values through the deployment pipeline.
// Never put a client secret, access token, refresh token, or other credential in this file.
window.TINLYT_RUNTIME_CONFIG = Object.freeze({
  apiBaseUrl: "/api/twi",
  apiAllowedOrigins: [],
  oauth: {
    authorizationEndpoint: "",
    tokenEndpoint: "",
    clientId: "",
    redirectUri: window.location.origin + "/auth/callback",
    scope: "",
    resource: "",
    trustedIssuerOrigins: []
  }
});
