import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import handler from "../api/early-access.js";

const root = fileURLToPath(new URL("../", import.meta.url));
const allowedOrigin = "https://tinlyt.tinlance.com";
const configuredEnv = {
  SUPABASE_URL: "https://project.supabase.co",
  SUPABASE_SECRET_KEY: "test-server-secret",
  SUPABASE_SERVICE_ROLE_KEY: "",
  RESEND_API_KEY: "test-resend-key",
  RESEND_FROM_EMAIL: "Tinlyt <hello@tinlance.com>",
  EARLY_ACCESS_NOTIFY_EMAIL: "team@tinlance.com",
  TURNSTILE_SECRET_KEY: "test-turnstile-secret",
  EARLY_ACCESS_RATE_LIMIT_SALT: "test-only-high-entropy-rate-limit-salt-0123456789",
  EARLY_ACCESS_PRIVACY_NOTICE_VERSION: "test-approved-notice-v1",
  EARLY_ACCESS_ALLOWED_ORIGIN: allowedOrigin
};

function responseRecorder() {
  return {
    headers: {},
    statusCode: 200,
    body: null,
    setHeader(name, value) { this.headers[name] = value; },
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; }
  };
}

async function withEnv(values, run) {
  const names = new Set([...Object.keys(values), ...Object.keys(configuredEnv)]);
  const original = Object.fromEntries([...names].map((name) => [name, process.env[name]]));
  for (const name of names) delete process.env[name];
  Object.assign(process.env, values);
  try {
    return await run();
  } finally {
    for (const name of names) {
      if (original[name] === undefined) delete process.env[name];
      else process.env[name] = original[name];
    }
  }
}

function request(body = {}, headers = {}) {
  return {
    method: "POST",
    headers: {
      origin: allowedOrigin,
      "content-type": "application/json",
      ...headers
    },
    body
  };
}

test("early-access endpoint rejects methods other than POST", async () => {
  const res = responseRecorder();
  await handler({ method: "GET", headers: {} }, res);
  assert.equal(res.statusCode, 405);
  assert.equal(res.headers.Allow, "POST");
  assert.equal(res.headers["Cache-Control"], "no-store");
});

test("early-access endpoint rejects cross-origin requests", async () => {
  const res = responseRecorder();
  await handler(request({}, { origin: "https://untrusted.example" }), res);
  assert.equal(res.statusCode, 403);
});

test("early-access endpoint rejects requests without an origin", async () => {
  const res = responseRecorder();
  await handler(request({}, { origin: undefined }), res);
  assert.equal(res.statusCode, 403);
});

test("early-access endpoint requires JSON", async () => {
  const res = responseRecorder();
  await handler(request({}, { "content-type": "text/plain" }), res);
  assert.equal(res.statusCode, 415);
});

test("early-access endpoint fails closed when server configuration is missing", async () => {
  const names = [
    "SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY",
    "RESEND_API_KEY", "RESEND_FROM_EMAIL", "EARLY_ACCESS_NOTIFY_EMAIL",
    "TURNSTILE_SECRET_KEY", "EARLY_ACCESS_RATE_LIMIT_SALT",
    "EARLY_ACCESS_PRIVACY_NOTICE_VERSION"
  ];
  const original = Object.fromEntries(names.map((name) => [name, process.env[name]]));
  for (const name of names) delete process.env[name];
  try {
    const res = responseRecorder();
    await handler(request({}), res);
    assert.equal(res.statusCode, 503);
    assert.match(res.body.error, /not configured/i);
  } finally {
    for (const name of names) {
      if (original[name] === undefined) delete process.env[name];
      else process.env[name] = original[name];
    }
  }
});

test("early-access endpoint rejects an unsupported use case before network access", async () => {
  await withEnv(configuredEnv, async () => {
    const res = responseRecorder();
    await handler(request({
      name: "Test Person",
      email: "person@example.com",
      useCase: "admin-access",
      consent: true,
      turnstileToken: "test-token"
    }), res);
    assert.equal(res.statusCode, 400);
  });
});

test("early-access endpoint requires an explicit privacy consent and Turnstile token", async () => {
  await withEnv(configuredEnv, async () => {
    const missingConsent = responseRecorder();
    await handler(request({
      name: "Test Person",
      email: "person@example.com",
      useCase: "web-research",
      consent: false,
      turnstileToken: "test-token"
    }), missingConsent);
    assert.equal(missingConsent.statusCode, 400);

    const missingToken = responseRecorder();
    await handler(request({
      name: "Test Person",
      email: "person@example.com",
      useCase: "web-research",
      consent: true,
      turnstileToken: ""
    }), missingToken);
    assert.equal(missingToken.statusCode, 400);
  });
});

test("honeypot submissions return a generic success without external calls", async () => {
  await withEnv(configuredEnv, async () => {
    const res = responseRecorder();
    await handler(request({ website: "bot-filled-value" }), res);
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.ok, true);
  });
});

test("Turnstile is permitted by the deployed Content Security Policy", async () => {
  const vercel = JSON.parse(await readFile(path.join(root, "vercel.json"), "utf8"));
  const policy = vercel.headers.flatMap((rule) => rule.headers)
    .find((header) => header.key === "Content-Security-Policy")?.value || "";
  assert.match(policy, /script-src[^;]*https:\/\/challenges\.cloudflare\.com/);
  assert.match(policy, /frame-src https:\/\/challenges\.cloudflare\.com/);
});

test("contact and demo pages load runtime config before the early-access handler", async () => {
  for (const pageName of ["contact.html", "book-demo.html"]) {
    const html = await readFile(path.join(root, pageName), "utf8");
    assert.match(html, /data-early-access-form/);
    assert.ok(html.indexOf("/runtime-config.js") < html.indexOf("/early-access.js"));
    assert.match(html, /name="consent"[^>]*required/);
    assert.match(html, /name="marketingOptIn"/);
  }
});


test("build injects only the public Turnstile site key into generated runtime config", async () => {
  const build = await readFile(path.join(root, "scripts/build.mjs"), "utf8");
  const runtime = await readFile(path.join(root, "runtime-config.js"), "utf8");
  assert.match(build, /process\.env\.EARLY_ACCESS_TURNSTILE_SITE_KEY/);
  assert.match(build, /JSON\.stringify\(siteKey\)/);
  assert.match(runtime, /earlyAccessTurnstileSiteKey: ""/);
  assert.doesNotMatch(runtime, /TURNSTILE_SECRET_KEY|SUPABASE_SECRET_KEY|RESEND_API_KEY/);
});

test("Supabase migration keeps intake private and rate-limit RPC least-privileged", async () => {
  const migrationPath = path.resolve(root, "../../supabase/migrations/20261022072400_early_access_requests.sql");
  const migration = await readFile(migrationPath, "utf8");
  assert.match(migration, /enable row level security/i);
  assert.match(migration, /revoke all on table public\.early_access_requests from public, anon, authenticated/i);
  assert.match(migration, /security invoker/i);
  assert.match(migration, /revoke all on function public\.consume_early_access_rate_limit[\s\S]*?from public, anon, authenticated/i);
  assert.match(migration, /grant update \(notification_status, confirmation_status, updated_at\)/i);
  assert.doesNotMatch(migration, /security definer/i);
  assert.doesNotMatch(migration, /grant all on table public\.early_access_requests/i);
});


test("early-access endpoint rejects insecure Supabase URLs and weak rate-limit salts", async () => {
  await withEnv({ ...configuredEnv, SUPABASE_URL: "http://127.0.0.1:5432" }, async () => {
    const res = responseRecorder();
    await handler(request({}), res);
    assert.equal(res.statusCode, 503);
  });
  await withEnv({ ...configuredEnv, EARLY_ACCESS_RATE_LIMIT_SALT: "short" }, async () => {
    const res = responseRecorder();
    await handler(request({}), res);
    assert.equal(res.statusCode, 503);
  });
});
