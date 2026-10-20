import { getRuntime } from "./app/runtime.js";
import { buildJobRequest, isTerminalJobStatus } from "./app/investigation.js";

const activeLinks = document.querySelectorAll('.nav-link');
for (const link of activeLinks) {
  link.addEventListener('click', () => {
    for (const candidate of activeLinks) {
      candidate.classList.remove('is-active');
      candidate.removeAttribute('aria-current');
    }
    link.classList.add('is-active');
    link.setAttribute('aria-current', 'page');
    const heading = document.querySelector('#breadcrumb-current');
    if (heading) heading.textContent = link.textContent.trim();
  });
}

const runtimeConfig = window.TINLYT_RUNTIME_CONFIG;
const runtime = getRuntime(runtimeConfig);
const signInButton = document.querySelector('#sign-in');
const modeTitle = document.querySelector('#mode-title');
const modeDescription = document.querySelector('#mode-description');
const sidebarStatus = document.querySelector('#runtime-message');
const systemState = document.querySelector('#system-state');
const environmentLabel = document.querySelector('#environment-label');
const connectionBadge = document.querySelector('#connection-badge');
const form = document.querySelector('#investigation-form');
const kindSelect = document.querySelector('#job-kind');
const questionField = document.querySelector('#question');
const limitField = document.querySelector('#search-limit');
const urlField = document.querySelector('#target-url');
const searchFields = document.querySelector('#search-fields');
const urlFields = document.querySelector('#url-fields');
const urlHelp = document.querySelector('#url-help');
const submitButton = document.querySelector('#submit-investigation');
const statusPanel = document.querySelector('#investigation-status');
const statusBadge = document.querySelector('#job-status-badge');
const statusMessage = document.querySelector('#job-status-message');
const metadataList = document.querySelector('#job-metadata');
const resultWrap = document.querySelector('#job-result-wrap');
const resultPre = document.querySelector('#job-result');
const refreshButton = document.querySelector('#refresh-job');

function showMode(title, description) {
  if (modeTitle) modeTitle.textContent = title;
  if (modeDescription) modeDescription.textContent = description;
}

function stripOAuthResponseParameters() {
  const url = new URL(window.location.href);
  for (const parameter of ['code', 'state', 'error', 'error_description', 'error_uri', 'iss', 'session_state']) {
    url.searchParams.delete(parameter);
  }
  window.history.replaceState(null, '', url.toString());
}

let callbackPath = null;
try {
  if (typeof runtimeConfig?.oauth?.redirectUri === 'string') callbackPath = new URL(runtimeConfig.oauth.redirectUri).pathname;
} catch {
  callbackPath = null;
}

let isAuthorized = false;
let activeJobId = null;
let submitting = false;

function setLiveControlsEnabled(enabled) {
  for (const control of [kindSelect, questionField, limitField, urlField, submitButton]) {
    if (control) control.disabled = !enabled;
  }
  if (signInButton && runtime.state === 'ready') {
    signInButton.disabled = false;
    signInButton.textContent = enabled ? 'Clear session' : 'Sign in';
    signInButton.setAttribute('aria-label', enabled ? 'Clear the local Tinlyt session' : 'Sign in to Tinlyt');
  }
  if (connectionBadge) connectionBadge.textContent = enabled ? 'Authenticated' : 'Not connected';
  if (systemState) systemState.textContent = enabled ? 'Identity ready' : 'API disconnected';
  if (environmentLabel) environmentLabel.textContent = enabled ? 'Authenticated session' : 'Foundation mode';
  if (sidebarStatus) sidebarStatus.textContent = enabled
    ? 'Authenticated. Job access is still governed by Platform scopes and TWI tenant/subject authorization.'
    : 'Sign in with the approved Platform identity provider to submit live jobs.';
}

function updateKindFields() {
  const kind = kindSelect?.value ?? 'search';
  if (searchFields) searchFields.hidden = kind !== 'search';
  if (urlFields) urlFields.hidden = kind === 'search';
  if (questionField) questionField.required = kind === 'search';
  if (urlField) urlField.required = kind !== 'search';
  if (urlHelp) urlHelp.textContent = kind === 'browser'
    ? 'Browser acquisition requires an absolute HTTPS URL on port 443. The service enforces network and browser policy.'
    : 'Fetch requires an absolute HTTP(S) URL. The service enforces URL safety policy.';
}
kindSelect?.addEventListener('change', updateKindFields);
updateKindFields();

function showJob(job, message) {
  if (!statusPanel) return;
  statusPanel.hidden = false;
  if (statusBadge) statusBadge.textContent = job.status;
  if (statusMessage) statusMessage.textContent = message;
  if (metadataList) {
    metadataList.replaceChildren();
    const entries = [
      ['Job ID', job.job_id],
      ['Operation', job.kind],
      ['Created', job.created_at],
      ['Last updated', job.updated_at],
      ['Attempts', String(job.attempts) + ' / ' + String(job.max_attempts)],
    ];
    for (const [label, value] of entries) {
      const term = document.createElement('dt');
      term.textContent = label;
      const description = document.createElement('dd');
      description.textContent = value;
      metadataList.append(term, description);
    }
  }
  const hasResult = job.status === 'succeeded' && job.result !== null;
  if (resultWrap) resultWrap.hidden = !hasResult;
  if (resultPre && hasResult) {
    let serialized = '';
    try { serialized = JSON.stringify(job.result, null, 2); } catch { serialized = '[Result could not be displayed]'; }
    const limit = 20_000;
    resultPre.textContent = serialized.length > limit
      ? serialized.slice(0, limit) + '\n… Output truncated in the interface. The API response was validated before rendering.'
      : serialized;
  }
  if (refreshButton) refreshButton.hidden = isTerminalJobStatus(job.status);
}

function wait(milliseconds) {
  return new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds));
}

async function refreshJob(showProgress = true) {
  if (!activeJobId || runtime.state !== 'ready' || !isAuthorized) return;
  try {
    const job = await runtime.apiClient.getJob(activeJobId);
    showJob(job, 'Current job state returned by TWI.');
    return job;
  } catch {
    if (statusMessage) statusMessage.textContent = 'The latest job state could not be retrieved. Check the connection and retry; the existing job may still be running.';
    if (refreshButton) refreshButton.hidden = false;
    return null;
  }
}

async function pollJob(initialJob) {
  let job = initialJob;
  for (let attempt = 0; attempt < 20 && !isTerminalJobStatus(job.status); attempt += 1) {
    await wait(1500);
    const updated = await refreshJob(false);
    if (!updated) return;
    job = updated;
  }
  if (!isTerminalJobStatus(job.status) && statusMessage) {
    statusMessage.textContent = 'The job is still active. Refresh status to request the latest state; no completion outcome is assumed.';
    if (refreshButton) refreshButton.hidden = false;
  }
}

form?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (submitting || !isAuthorized || runtime.state !== 'ready') {
    showMode('Sign-in required', 'Complete the approved Platform sign-in before submitting a live investigation.');
    return;
  }
  let request;
  try {
    request = buildJobRequest(kindSelect.value, questionField.value, urlField.value, limitField.value);
  } catch (error) {
    if (statusPanel) statusPanel.hidden = false;
    if (statusMessage) statusMessage.textContent = error instanceof Error ? error.message : 'The investigation request is invalid.';
    if (statusBadge) statusBadge.textContent = 'Invalid request';
    return;
  }
  submitting = true;
  submitButton.disabled = true;
  submitButton.textContent = 'Submitting…';
  if (statusPanel) statusPanel.hidden = false;
  if (statusBadge) statusBadge.textContent = 'Submitting';
  if (statusMessage) statusMessage.textContent = 'Sending the request to TWI. No result is assumed until the service returns it.';
  if (metadataList) metadataList.replaceChildren();
  if (resultWrap) resultWrap.hidden = true;
  if (refreshButton) refreshButton.hidden = true;
  try {
    const job = await runtime.apiClient.createJob(request);
    activeJobId = job.job_id;
    showJob(job, 'TWI accepted the request. Waiting for the service-reported job state.');
    await pollJob(job);
  } catch (error) {
    if (statusBadge) statusBadge.textContent = 'Submission failed';
    if (statusMessage) statusMessage.textContent = error instanceof Error
      ? error.message
      : 'The request could not be completed. No automatic retry was performed.';
    if (refreshButton) refreshButton.hidden = !activeJobId;
  } finally {
    submitting = false;
    if (submitButton) {
      submitButton.disabled = !isAuthorized;
      submitButton.innerHTML = 'Start investigation <span aria-hidden="true">→</span>';
    }
  }
});

refreshButton?.addEventListener('click', () => { void refreshJob(); });

if (runtime.state === 'ready') {
  setLiveControlsEnabled(false);
  showMode('Identity configuration ready', 'Deployment settings are present. Sign in with the approved Platform identity provider to submit an authenticated search, fetch, or browser job.');
} else if (runtime.state === 'invalid_configuration') {
  setLiveControlsEnabled(false);
  showMode('Identity configuration invalid', 'Live operations are disabled because the approved Platform identity or TWI API configuration is invalid.');
} else {
  setLiveControlsEnabled(false);
}

if (signInButton && runtime.state === 'ready') {
  signInButton.disabled = false;
  signInButton.textContent = 'Sign in';
  signInButton.setAttribute('aria-label', 'Sign in to Tinlyt');
  signInButton.addEventListener('click', async () => {
    if (isAuthorized) {
      runtime.clearSession();
      isAuthorized = false;
      setLiveControlsEnabled(false);
      showMode('Local session cleared', 'The in-memory TWI access token was cleared. The external identity-provider session may remain active.');
      return;
    }
    signInButton.disabled = true;
    try {
      await runtime.beginLogin();
    } catch {
      showMode('Sign-in unavailable', 'The approved Platform identity flow could not be started. No API-backed operation was performed.');
      signInButton.disabled = false;
    }
  });
} else if (signInButton) {
  signInButton.disabled = true;
  signInButton.title = runtime.message;
}

const currentUrl = new URL(window.location.href);
const hasOAuthResponse = ['code', 'state', 'error', 'error_description', 'error_uri', 'iss', 'session_state']
  .some((parameter) => currentUrl.searchParams.has(parameter));
const isExpectedCallback = Boolean(callbackPath && currentUrl.pathname === callbackPath);

if (hasOAuthResponse && runtime.state === 'ready' && isExpectedCallback) {
  runtime.handleCallback().then(() => {
    isAuthorized = true;
    setLiveControlsEnabled(true);
    stripOAuthResponseParameters();
    showMode('Identity authorization completed', 'The short-lived access token is held in memory only. Requests are sent to TWI and remain subject to server-enforced scopes and tenant/subject boundaries.');
  }).catch(() => {
    stripOAuthResponseParameters();
    setLiveControlsEnabled(false);
    if (signInButton) signInButton.disabled = false;
    showMode('Sign-in failed', 'The configured identity flow did not complete. No investigation or evidence operation was started.');
  });
} else if (hasOAuthResponse) {
  stripOAuthResponseParameters();
  showMode('Sign-in unavailable', 'The OAuth response could not be processed because the approved deployment configuration or callback route is missing. No API-backed operation was performed.');
}
