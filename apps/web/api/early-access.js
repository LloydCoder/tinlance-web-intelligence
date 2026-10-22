import { createHash } from "node:crypto";

const json = (res, status, body) => {
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.status(status).json(body);
};
const text = (value, max) => typeof value === "string" ? value.trim().slice(0, max) : "";
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const allowedUseCases = new Set(["web-research", "competitive-intelligence", "due-diligence", "investigations", "data-extraction", "agent-integration", "other"]);

async function verifyTurnstile(token, secret, remoteIp) {
  const body = new URLSearchParams({ secret, response: token });
  if (remoteIp) body.set("remoteip", remoteIp);
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
    signal: AbortSignal.timeout(5000)
  });
  if (!response.ok) return false;
  return (await response.json()).success === true;
}
async function sendEmail(apiKey, payload) {
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: "Bearer " + apiKey, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(8000)
  });
  if (!response.ok) throw new Error("Email provider returned " + response.status);
  return response.json();
}
const escapeHtml = (value) => String(value || "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
})[character]);

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return json(res, 405, { error: "Method not allowed." });
  }
  const origin = req.headers.origin;
  const allowedOrigin = process.env.EARLY_ACCESS_ALLOWED_ORIGIN || "https://tinlyt.tinlance.com";
  if (origin && origin !== allowedOrigin) return json(res, 403, { error: "Request origin not allowed." });

  const supabaseKeyName = process.env.SUPABASE_SECRET_KEY ? "SUPABASE_SECRET_KEY" : "SUPABASE_SERVICE_ROLE_KEY";
  const required = ["SUPABASE_URL", supabaseKeyName, "RESEND_API_KEY", "RESEND_FROM_EMAIL", "EARLY_ACCESS_NOTIFY_EMAIL", "TURNSTILE_SECRET_KEY"];
  if (required.some((key) => !process.env[key])) {
    return json(res, 503, { error: "Early access requests are not configured yet. Please try again later." });
  }
  const body = req.body && typeof req.body === "object" ? req.body : {};
  if (JSON.stringify(body).length > 12000) return json(res, 413, { error: "Request is too large." });
  if (text(body.website, 200)) return json(res, 200, { ok: true });

  const name = text(body.name, 120);
  const email = text(body.email, 254).toLowerCase();
  const company = text(body.company, 160);
  const role = text(body.role, 100);
  const useCase = text(body.useCase, 80);
  const description = text(body.description, 2000);
  const consent = body.consent === true;
  const marketingOptIn = body.marketingOptIn === true;
  const turnstileToken = text(body.turnstileToken, 4096);
  if (name.length < 2 || !emailPattern.test(email) || !allowedUseCases.has(useCase) || !consent || !turnstileToken) {
    return json(res, 400, { error: "Check the required fields and complete the anti-bot check." });
  }

  const forwarded = text(req.headers["x-forwarded-for"], 512).split(",")[0].trim();
  const remoteIp = forwarded && /^[0-9a-fA-F:.]+$/.test(forwarded) ? forwarded : "";
  try {
    if (!await verifyTurnstile(turnstileToken, process.env.TURNSTILE_SECRET_KEY, remoteIp)) {
      return json(res, 400, { error: "The anti-bot check expired or could not be verified. Please try again." });
    }
  } catch {
    return json(res, 503, { error: "The anti-bot service is temporarily unavailable. Please try again." });
  }

  const supabaseUrl = process.env.SUPABASE_URL.replace(/\/$/, "");
  const supabaseKey = process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const emailHash = createHash("sha256").update(email).digest("hex");
  const record = {
    name, email, email_hash: emailHash, company: company || null, role: role || null,
    use_case: useCase, description: description || null, consent_at: new Date().toISOString(),
    marketing_opt_in: marketingOptIn, source: "tinlyt-public-website", status: "new"
  };
  let stored;
  try {
    const response = await fetch(supabaseUrl + "/rest/v1/early_access_requests?select=id,created_at", {
      method: "POST",
      headers: {
        apikey: supabaseKey, Authorization: "Bearer " + supabaseKey,
        "Content-Type": "application/json", Prefer: "return=representation"
      },
      body: JSON.stringify(record), signal: AbortSignal.timeout(8000)
    });
    if (response.status === 409) {
      return json(res, 200, { ok: true, message: "If this address has not already been submitted, your request is now in the review queue." });
    }
    if (!response.ok) throw new Error("Database returned " + response.status);
    stored = (await response.json())[0];
    if (!stored || !stored.id) throw new Error("Database did not return a request identifier");
  } catch {
    return json(res, 503, { error: "We could not safely save your request. No request was confirmed; please try again shortly." });
  }

  const safeName = escapeHtml(name);
  const safeEmail = escapeHtml(email);
  const safeCompany = escapeHtml(company || "Not provided");
  const safeRole = escapeHtml(role || "Not provided");
  const safeUseCase = escapeHtml(useCase);
  const safeDescription = escapeHtml(description || "Not provided").replace(/\n/g, "<br>");
  const requestId = escapeHtml(stored.id);

  const mailResults = await Promise.allSettled([
    sendEmail(process.env.RESEND_API_KEY, {
      from: process.env.RESEND_FROM_EMAIL, to: [process.env.EARLY_ACCESS_NOTIFY_EMAIL],
      subject: "New Tinlyt early-access request — " + useCase,
      html: "<h2>New Tinlyt early-access request</h2><p><strong>Request ID:</strong> " + requestId +
        "</p><p><strong>Name:</strong> " + safeName + "</p><p><strong>Email:</strong> " + safeEmail +
        "</p><p><strong>Company:</strong> " + safeCompany + "</p><p><strong>Role:</strong> " + safeRole +
        "</p><p><strong>Use case:</strong> " + safeUseCase + "</p><p><strong>Workflow:</strong><br>" +
        safeDescription + "</p><p><strong>Marketing opt-in:</strong> " + (marketingOptIn ? "Yes" : "No") + "</p>"
    }),
    sendEmail(process.env.RESEND_API_KEY, {
      from: process.env.RESEND_FROM_EMAIL, to: [email],
      subject: "We received your Tinlyt early-access request",
      html: "<p>Hello " + safeName + ",</p><p>We received your request to evaluate Tinlyt. Our team will review the use case; this message does not guarantee acceptance or immediate workspace access.</p><p>Reference: " + requestId + "</p><p>If you did not submit this request, you can ignore this message.</p>"
    })
  ]);

  const notificationStatus = mailResults[0].status === "fulfilled" ? "sent" : "failed";
  const confirmationStatus = mailResults[1].status === "fulfilled" ? "sent" : "failed";
  try {
    await fetch(supabaseUrl + "/rest/v1/early_access_requests?id=eq." + encodeURIComponent(stored.id), {
      method: "PATCH",
      headers: {
        apikey: supabaseKey, Authorization: "Bearer " + supabaseKey,
        "Content-Type": "application/json", Prefer: "return=minimal"
      },
      body: JSON.stringify({ notification_status: notificationStatus, confirmation_status: confirmationStatus, updated_at: new Date().toISOString() }),
      signal: AbortSignal.timeout(5000)
    });
  } catch {
    // Preserve successful submission; storage remains authoritative if delivery metadata cannot be updated.
  }
  return json(res, 201, {
    ok: true,
    message: "Your request has been received for review. We will contact you by email if we need more information."
  });
}
