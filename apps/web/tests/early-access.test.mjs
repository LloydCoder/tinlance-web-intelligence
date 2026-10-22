import test from "node:test";
import assert from "node:assert/strict";
import handler from "../api/early-access.js";

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

test("early-access endpoint rejects methods other than POST", async () => {
  const res = responseRecorder();
  await handler({ method: "GET", headers: {} }, res);
  assert.equal(res.statusCode, 405);
  assert.equal(res.headers.Allow, "POST");
});

test("early-access endpoint rejects cross-origin requests", async () => {
  const res = responseRecorder();
  await handler({ method: "POST", headers: { origin: "https://untrusted.example" }, body: {} }, res);
  assert.equal(res.statusCode, 403);
});

test("early-access endpoint fails closed when secrets are not configured", async () => {
  const names = ["SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "RESEND_API_KEY", "RESEND_FROM_EMAIL", "EARLY_ACCESS_NOTIFY_EMAIL", "TURNSTILE_SECRET_KEY"];
  const original = Object.fromEntries(names.map((name) => [name, process.env[name]]));
  for (const name of names) delete process.env[name];
  try {
    const res = responseRecorder();
    await handler({ method: "POST", headers: { origin: "https://tinlyt.tinlance.com" }, body: {} }, res);
    assert.equal(res.statusCode, 503);
    assert.match(res.body.error, /not configured/i);
  } finally {
    for (const name of names) {
      if (original[name] === undefined) delete process.env[name];
      else process.env[name] = original[name];
    }
  }
});
