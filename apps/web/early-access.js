(() => {
  "use strict";
  const form = document.querySelector("[data-early-access-form]");
  if (!form) return;
  const status = form.querySelector("[data-form-status]");
  const submit = form.querySelector('button[type="submit"]');
  const tokenField = form.querySelector('[name="turnstileToken"]');
  const config = window.TINLYT_RUNTIME_CONFIG || {};
  const siteKey = config.earlyAccessTurnstileSiteKey || "";
  let widgetId = null;

  const showStatus = (message, kind) => {
    status.textContent = message;
    status.dataset.kind = kind;
    status.setAttribute("role", kind === "error" ? "alert" : "status");
  };
  const renderTurnstile = () => {
    if (!window.turnstile || widgetId !== null) return;
    const container = form.querySelector("[data-turnstile]");
    if (!container) return;
    try {
      widgetId = window.turnstile.render(container, {
      sitekey: siteKey,
      callback: (token) => { tokenField.value = token; },
      "expired-callback": () => { tokenField.value = ""; },
      "error-callback": () => { tokenField.value = ""; showStatus("The anti-bot check failed. Please try again.", "error"); }
      });
      submit.disabled = false;
      showStatus("Complete the anti-bot check, then submit your request.", "ready");
    } catch {
      submit.disabled = true;
      showStatus("The anti-bot check could not initialize. Please refresh and try again.", "error");
    }
  };
  const loadTurnstile = () => {
    if (!siteKey) {
      showStatus("Early access is not activated yet. Please check back soon.", "error");
      submit.disabled = true;
      return;
    }
    if (window.turnstile) return renderTurnstile();
    if (document.querySelector('script[data-turnstile-loader]')) return;
    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    script.defer = true;
    script.dataset.turnstileLoader = "true";
    script.onload = renderTurnstile;
    script.onerror = () => { submit.disabled = true; showStatus("The anti-bot check could not load. Please refresh and try again.", "error"); };
    document.head.append(script);
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    if (!tokenField.value) {
      showStatus("Complete the anti-bot check before submitting.", "error");
      return;
    }
    submit.disabled = true;
    showStatus("Submitting your request…", "pending");
    const data = new FormData(form);
    const payload = {
      name: String(data.get("name") || ""),
      email: String(data.get("email") || ""),
      company: String(data.get("company") || ""),
      role: String(data.get("role") || ""),
      useCase: String(data.get("useCase") || ""),
      description: String(data.get("description") || ""),
      consent: data.get("consent") === "on",
      marketingOptIn: data.get("marketingOptIn") === "on",
      turnstileToken: tokenField.value,
      website: String(data.get("website") || "")
    };
    try {
      const response = await fetch("/api/early-access", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
        credentials: "same-origin"
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.ok !== true) throw new Error(result.error || "We could not submit your request. Please try again.");
      form.reset();
      if (window.turnstile && widgetId !== null) window.turnstile.reset(widgetId);
      tokenField.value = "";
      showStatus(result.message || "Your request has been received for review.", "success");
    } catch (error) {
      if (window.turnstile && widgetId !== null) window.turnstile.reset(widgetId);
      tokenField.value = "";
      showStatus(error instanceof Error ? error.message : "Submission failed. Please try again.", "error");
    } finally {
      submit.disabled = false;
    }
  });
  loadTurnstile();
})();
