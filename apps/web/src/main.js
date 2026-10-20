import { getRuntime } from "./app/runtime.js";
import { buildJobRequest, isTerminalJobStatus } from "./app/investigation.js";

const developerCopyStatus = document.querySelector('#developer-copy-status');
const developerCopyButtons = document.querySelectorAll('[data-copy-target]');
for (const button of developerCopyButtons) {
  button.addEventListener('click', async () => {
    const targetId = button.getAttribute('data-copy-target');
    const target = targetId ? document.getElementById(targetId) : null;
    const value = target?.textContent ?? '';
    if (!value) {
      if (developerCopyStatus) developerCopyStatus.textContent = 'This example is unavailable.';
      return;
    }
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(value);
      if (developerCopyStatus) developerCopyStatus.textContent = 'Example copied. Replace template values and keep credentials in your trusted runtime.';
    } catch {
      if (developerCopyStatus) developerCopyStatus.textContent = 'Clipboard access is unavailable in this context. Select and copy the example manually; no request was sent.';
    }
  });
}
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
const resultContainer = document.querySelector('#job-result');
const refreshButton = document.querySelector('#refresh-job');
const cancelJobButton = document.querySelector('#cancel-job');
const exportEvidenceButton = document.querySelector('#export-evidence');
const evidencePanel = document.querySelector('#evidence');
const evidenceStatus = document.querySelector('#evidence-status');
const evidenceIntegrityBadge = document.querySelector('#evidence-integrity-badge');
const evidenceMetadata = document.querySelector('#evidence-metadata');
const downloadEvidenceButton = document.querySelector('#download-evidence');
const runLookupForm = document.querySelector('#run-lookup-form');
const runIdField = document.querySelector('#run-id');
const lookupButton = document.querySelector('#lookup-run');
const verificationForm = document.querySelector('#verification-form');
const claimIdField = document.querySelector('#claim-id');
const claimStatementField = document.querySelector('#claim-statement');
const verificationCitations = document.querySelector('#verification-citations');
const citationCount = document.querySelector('#citation-count');
const addCitationButton = document.querySelector('#add-citation');
const verifyClaimButton = document.querySelector('#verify-claim');
const verificationStatus = document.querySelector('#verification-status');
const verificationResult = document.querySelector('#verification-result');
const verificationMetadata = document.querySelector('#verification-metadata');
const verifiedClaims = document.querySelector('#verified-claims');
const monitorCreateForm = document.querySelector('#monitor-create-form');
const monitorTargetUrlField = document.querySelector('#monitor-target-url');
const monitorMaxBytesField = document.querySelector('#monitor-max-bytes');
const createMonitorButton = document.querySelector('#create-monitor');
const monitorLookupForm = document.querySelector('#monitor-lookup-form');
const monitorIdField = document.querySelector('#monitor-id');
const lookupMonitorButton = document.querySelector('#lookup-monitor');
const monitorStatus = document.querySelector('#monitor-status');
const monitorDetails = document.querySelector('#monitor-details');
const monitorMetadata = document.querySelector('#monitor-metadata');
const runMonitorButton = document.querySelector('#run-monitor');
const pauseMonitorButton = document.querySelector('#pause-monitor');
const resumeMonitorButton = document.querySelector('#resume-monitor');
const deleteMonitorButton = document.querySelector('#delete-monitor');
const monitorRunStatus = document.querySelector('#monitor-run-status');
const refreshMonitorRunButton = document.querySelector('#refresh-monitor-run');
const monitorRunMetadata = document.querySelector('#monitor-run-metadata');
const monitorRunLookupForm = document.querySelector('#monitor-run-lookup-form');
const monitorRunIdField = document.querySelector('#monitor-run-id');
const lookupMonitorRunButton = document.querySelector('#lookup-monitor-run');
const usageForm = document.querySelector('#usage-form');
const usageDimensionField = document.querySelector('#usage-dimension');
const usagePeriodField = document.querySelector('#usage-period-start');
const usageLimitField = document.querySelector('#usage-limit');
const usageCursorField = document.querySelector('#usage-cursor');
const loadUsageButton = document.querySelector('#load-usage');
const loadNextUsagePageButton = document.querySelector('#load-next-usage-page');
const usageStatus = document.querySelector('#usage-status');
const usageResults = document.querySelector('#usage-results');
const usageSummary = document.querySelector('#usage-summary');
const usageEvents = document.querySelector('#usage-events');

function clearUsageView() {
  latestUsageQuery = null;
  latestUsageCursor = null;
  usageLoading = false;
  if (usageResults) usageResults.hidden = true;
  if (usageSummary) usageSummary.replaceChildren();
  if (usageEvents) usageEvents.replaceChildren();
  if (usageCursorField) usageCursorField.value = '';
  if (loadUsageButton) loadUsageButton.disabled = !isAuthorized;
  if (loadNextUsagePageButton) { loadNextUsagePageButton.hidden = true; loadNextUsagePageButton.disabled = true; }
  if (usageStatus) usageStatus.textContent = runtime.state === 'ready'
    ? 'Sign in with the approved Platform identity provider and provide a period start to load usage.'
    : 'Usage is disabled because the approved identity configuration is not ready.';
}

function appendUsageSummary(label, value) {
  const term = document.createElement('dt');
  term.textContent = label;
  const description = document.createElement('dd');
  description.textContent = value;
  usageSummary?.append(term, description);
}

function renderUsageResponse(response, append = false) {
  if (!append) {
    usageSummary?.replaceChildren();
    usageEvents?.replaceChildren();
    appendUsageSummary('Dimension', response.dimension);
    appendUsageSummary('Period start (UTC)', response.period_start);
    appendUsageSummary('Committed usage', String(response.used));
    appendUsageSummary('Quota limit', response.quota_limit === null ? 'Not configured / unavailable' : String(response.quota_limit));
    appendUsageSummary('Remaining allowance', response.remaining === null ? 'Not configured / unavailable' : String(response.remaining));
    appendUsageSummary('Plan', response.plan_id === null ? 'Not provided' : response.plan_id);
    appendUsageSummary('Plan version', response.plan_version === null ? 'Not provided' : String(response.plan_version));
  }
  for (const event of response.events) {
    const row = document.createElement('tr');
    for (const value of [event.occurred_at, event.feature, String(event.quantity), event.event_id]) {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.append(cell);
    }
    usageEvents?.append(row);
  }
  if (usageResults) usageResults.hidden = false;
  latestUsageCursor = response.next_cursor;
  if (loadNextUsagePageButton) {
    loadNextUsagePageButton.hidden = !response.has_more;
    loadNextUsagePageButton.disabled = !isAuthorized || usageLoading || !response.has_more;
  }
  if (usageStatus) usageStatus.textContent = response.has_more
    ? `Loaded ${response.returned} usage fact(s). More results are available; use Load next page to continue.`
    : `Loaded ${response.returned} usage fact(s). This page is complete for the requested cursor position.`;
}

async function loadUsage(query, append = false) {
  if (!isAuthorized || usageLoading || !runtime.apiClient) return;
  const requestSessionEpoch = authSessionEpoch;
  usageLoading = true;
  if (loadUsageButton) loadUsageButton.disabled = true;
  if (loadNextUsagePageButton) loadNextUsagePageButton.disabled = true;
  if (usageStatus) usageStatus.textContent = 'Loading tenant-scoped usage from TWI…';
  try {
    const response = await runtime.apiClient.readUsage(query);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    latestUsageQuery = { dimension: query.dimension, period_start: query.period_start, limit: query.limit };
    renderUsageResponse(response, append);
  } catch (error) {
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    if (!append) {
      if (usageResults) usageResults.hidden = true;
      if (usageSummary) usageSummary.replaceChildren();
      if (usageEvents) usageEvents.replaceChildren();
    }
    if (usageStatus) usageStatus.textContent = error instanceof Error
      ? error.message
      : 'Usage could not be loaded. No usage values have been inferred or fabricated.';
  } finally {
    if (authSessionEpoch === requestSessionEpoch) {
      usageLoading = false;
      if (isAuthorized && loadUsageButton) loadUsageButton.disabled = false;
      if (loadNextUsagePageButton) loadNextUsagePageButton.disabled = !isAuthorized || !latestUsageCursor;
    }
  }
}
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
let authSessionEpoch = 0;
let activeJobId = null;
let submitting = false;
let polling = false;
let cancelling = false;
let latestJob = null;
let exportingEvidence = false;
let currentEvidenceBytes = null;
let currentEvidenceJobId = null;
let verifying = false;
let citationRowSequence = 1;
let activeMonitor = null;
let activeMonitorRunId = null;
let activeMonitorRunStatus = null;
let monitorBusy = false;
let monitorRunPolling = false;
let pendingMonitorCreateFingerprint = null;
let pendingMonitorCreateKey = null;
let pendingMonitorRunMonitorId = null;
let pendingMonitorRunKey = null;
let usageLoading = false;
let latestUsageQuery = null;
let latestUsageCursor = null;

function setLiveControlsEnabled(enabled) {
  authSessionEpoch += 1;
  for (const control of [kindSelect, questionField, limitField, urlField, submitButton, runIdField, lookupButton, verifyClaimButton, monitorTargetUrlField, monitorMaxBytesField, createMonitorButton, monitorIdField, lookupMonitorButton, runMonitorButton, pauseMonitorButton, resumeMonitorButton, deleteMonitorButton, monitorRunIdField, lookupMonitorRunButton, usageDimensionField, usagePeriodField, usageLimitField, usageCursorField, loadUsageButton, loadNextUsagePageButton]) {
    if (control) control.disabled = !enabled;
  }
  if (signInButton && runtime.state === 'ready') {
    signInButton.disabled = false;
    signInButton.textContent = enabled ? 'Clear session' : 'Sign in';
    signInButton.setAttribute('aria-label', enabled ? 'Clear the local Tinlyt session' : 'Sign in to Tinlyt');
  }
  if (refreshButton) refreshButton.disabled = !enabled || polling || cancelling;
  if (!enabled) {
    activeJobId = null;
    latestJob = null;
    if (statusPanel) statusPanel.hidden = true;
    if (metadataList) metadataList.replaceChildren();
    if (resultContainer) resultContainer.replaceChildren();
    if (resultWrap) resultWrap.hidden = true;
    if (refreshButton) refreshButton.hidden = true;
    if (cancelJobButton) {
      cancelJobButton.hidden = true;
      cancelJobButton.disabled = true;
    }
    if (exportEvidenceButton) {
      exportEvidenceButton.hidden = true;
      exportEvidenceButton.disabled = true;
    }
    clearEvidenceView();
    clearVerificationView();
    clearMonitorView();
    clearUsageView();
  }
  if (connectionBadge) connectionBadge.textContent = enabled ? 'Authenticated' : 'Not connected';
  if (systemState) systemState.textContent = enabled ? 'Identity ready' : 'API disconnected';
  if (environmentLabel) environmentLabel.textContent = enabled ? 'Authenticated session' : 'Foundation mode';
  if (sidebarStatus) sidebarStatus.textContent = enabled
    ? 'Authenticated. Job access is still governed by Platform scopes and TWI tenant/subject authorization.'
    : 'Sign in with the approved Platform identity provider to submit live jobs.';
  if (enabled && !currentEvidenceJobId && evidenceStatus) {
    evidenceStatus.textContent = 'Submit or load a successful fetch job, then choose “Inspect and export evidence” to retrieve its package.';
  }
  if (enabled && verificationStatus && (!verificationResult || verificationResult.hidden)) {
    verificationStatus.textContent = 'Enter a claim and exact citations from captured text, then submit to compare the quotes with TWI evidence.';
  }
  updateVerificationControls();
  updateMonitorControls();
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

function safeWebUrl(value) {
  if (typeof value !== 'string' || value.length > 2048) return null;
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return null;
    return url.toString();
  } catch {
    return null;
  }
}

function appendText(parent, tagName, className, value) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = typeof value === 'string' ? value : String(value);
  parent.append(element);
  return element;
}

function appendSourceLink(parent, urlValue, label) {
  const safeUrl = safeWebUrl(urlValue);
  if (!safeUrl) {
    appendText(parent, 'p', 'source-url', typeof urlValue === 'string' ? urlValue.slice(0, 2048) : 'Source URL unavailable');
    return;
  }
  const link = document.createElement('a');
  link.href = safeUrl;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.referrerPolicy = 'no-referrer';
  link.textContent = label;
  parent.append(link);
}

function renderSearchResults(container, result) {
  if (!Array.isArray(result.results)) return false;
  const heading = appendText(container, 'p', 'result-summary', result.results.length + ' result record(s) returned by TWI');
  heading.setAttribute('aria-live', 'polite');
  if (typeof result.provider === 'string' && result.provider.length <= 100) {
    appendText(container, 'p', 'result-provider', 'Search provider: ' + result.provider);
  }
  if (result.results.length === 0) {
    appendText(container, 'p', 'result-empty', 'TWI returned no search results for this job.');
    return true;
  }
  for (const item of result.results.slice(0, 20)) {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      appendText(container, 'pre', 'result-json', JSON.stringify(item).slice(0, 1000));
      continue;
    }
    const card = document.createElement('article');
    card.className = 'source-result';
    const title = typeof item.title === 'string' ? item.title.slice(0, 500) : 'Untitled source';
    appendText(card, 'h4', 'source-result-title', title);
    if (Number.isInteger(item.rank) && item.rank > 0) appendText(card, 'span', 'source-rank', 'Rank ' + item.rank);
    appendSourceLink(card, item.url, safeWebUrl(item.url) ?? 'Source URL unavailable');
    if (typeof item.snippet === 'string' && item.snippet) appendText(card, 'p', 'source-snippet', item.snippet.slice(0, 2000));
    if (typeof item.provider === 'string' && item.provider.length <= 100) appendText(card, 'small', 'source-provider', item.provider);
    container.append(card);
  }
  if (result.results.length > 20) appendText(container, 'p', 'field-help', 'Only the first 20 result records are displayed here.');
  return true;
}

function renderFetchResult(container, result) {
  if (typeof result.source_url !== 'string' || typeof result.content_sha256 !== 'string') return false;
  appendText(container, 'p', 'result-summary', 'Captured page response returned by TWI');
  if (typeof result.title === 'string' && result.title) appendText(container, 'h4', 'source-result-title', result.title.slice(0, 500));
  appendSourceLink(container, result.source_url, safeWebUrl(result.source_url) ?? 'Source URL unavailable');
  const metadata = [
    ['HTTP status', result.status_code],
    ['Retrieved at', result.retrieved_at],
    ['Content type', result.content_type],
    ['SHA-256 content digest', result.content_sha256],
  ];
  const definitionList = document.createElement('dl');
  definitionList.className = 'job-metadata';
  for (const [label, value] of metadata) {
    if (typeof value !== 'string' && typeof value !== 'number') continue;
    appendText(definitionList, 'dt', '', label);
    appendText(definitionList, 'dd', '', String(value).slice(0, 512));
  }
  container.append(definitionList);
  if (typeof result.description === 'string' && result.description) appendText(container, 'p', 'source-snippet', result.description.slice(0, 2000));
  if (typeof result.text === 'string' && result.text) {
    appendText(container, 'h4', 'source-result-title', 'Captured text preview');
    appendText(container, 'pre', 'result-json', result.text.slice(0, 8000));
    if (result.text.length > 8000) appendText(container, 'p', 'field-help', 'Captured text preview truncated to 8,000 characters in the interface.');
  }
  return true;
}

function renderJobResult(job) {
  if (!resultContainer) return;
  resultContainer.replaceChildren();
  const result = job.result;
  if (job.kind === 'search' && renderSearchResults(resultContainer, result)) return;
  if (job.kind === 'fetch' && renderFetchResult(resultContainer, result)) return;
  let serialized = '';
  try { serialized = JSON.stringify(result, null, 2); } catch { serialized = '[Result could not be displayed]'; }
  const limit = 20_000;
  appendText(resultContainer, 'pre', 'result-json', serialized.length > limit
    ? serialized.slice(0, limit) + '\n… Output truncated in the interface. The API response was validated before rendering.'
    : serialized);
}

function clearEvidenceView() {
  currentEvidenceBytes = null;
  currentEvidenceJobId = null;
  if (evidencePanel) evidencePanel.hidden = false;
  if (evidenceStatus) evidenceStatus.textContent = !isAuthorized
    ? runtime.state === 'ready'
      ? 'Sign in with the approved Platform identity provider to inspect evidence from an accessible successful fetch job.'
      : 'Evidence export is disabled because the approved identity configuration is not ready.'
    : 'Submit or load a successful fetch job, then choose “Inspect and export evidence” to retrieve its package.';
  if (evidenceMetadata) evidenceMetadata.replaceChildren();
  if (evidenceIntegrityBadge) evidenceIntegrityBadge.textContent = 'Awaiting package';
  if (downloadEvidenceButton) downloadEvidenceButton.disabled = true;
}

function renderEvidencePackage(jobId, evidence, bytes) {
  currentEvidenceBytes = bytes;
  currentEvidenceJobId = jobId;
  if (evidencePanel) evidencePanel.hidden = false;
  if (evidenceIntegrityBadge) evidenceIntegrityBadge.textContent = 'Digest verified';
  if (evidenceStatus) {
    evidenceStatus.textContent = 'Package schema, captured byte size, and content SHA-256 validated. This detects content modification; it is not a digital signature or a truth verdict.';
  }
  if (evidenceMetadata) {
    evidenceMetadata.replaceChildren();
    const entries = [
      ['Format', evidence.format],
      ['Schema version', evidence.schema_version],
      ['Export ID', evidence.export_id],
      ['Artifact ID', evidence.artifact_id],
      ['Captured content SHA-256', evidence.content_sha256],
      ['Content type', evidence.content_type],
      ['Captured bytes', String(evidence.byte_size)],
      ['Source revision', evidence.source_revision],
      ['Observed HTTP status', String(evidence.provenance.status_code)],
      ['Retrieved at', evidence.provenance.retrieved_at],
      ['Requested URL SHA-256', evidence.provenance.requested_url_sha256],
      ['Final URL SHA-256', evidence.provenance.final_url_sha256],
      ['Redirect count', String(evidence.provenance.redirect_count)],
      ['Extractor version', evidence.provenance.extractor_version],
      ['Interpretation', 'Acquisition observation; source truth and source authority not assessed'],
    ];
    for (const [label, value] of entries) {
      const term = document.createElement('dt');
      term.textContent = label;
      const description = document.createElement('dd');
      description.textContent = value;
      evidenceMetadata.append(term, description);
    }
  }
  if (downloadEvidenceButton) downloadEvidenceButton.disabled = !isAuthorized || !(bytes instanceof Uint8Array);
}

function downloadExactEvidencePackage() {
  if (!isAuthorized || !currentEvidenceBytes || !currentEvidenceJobId) return;
  const blob = new Blob([currentEvidenceBytes], { type: 'application/vnd.tinlance.twi-evidence+json' });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = `twi-evidence-${currentEvidenceJobId}.json`;
  link.rel = 'noopener';
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  globalThis.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

function getCitationRows() {
  return verificationCitations
    ? Array.from(verificationCitations.querySelectorAll('[data-citation-row]'))
    : [];
}

function updateVerificationControls() {
  const rows = getCitationRows();
  if (verifyClaimButton) verifyClaimButton.disabled = !isAuthorized || submitting || polling || verifying;
  if (addCitationButton) addCitationButton.disabled = verifying || rows.length >= 4;
  if (citationCount) citationCount.textContent = `${rows.length} / 4`;
  rows.forEach((row, index) => {
    const legend = row.querySelector('legend');
    if (legend) legend.textContent = `Citation ${index + 1}`;
    const removeButton = row.querySelector('.remove-citation');
    if (removeButton) {
      removeButton.hidden = rows.length <= 1;
      removeButton.disabled = rows.length <= 1 || verifying;
    }
  });
}

function clearVerificationResult(message) {
  if (verificationResult) verificationResult.hidden = true;
  if (verificationMetadata) verificationMetadata.replaceChildren();
  if (verifiedClaims) verifiedClaims.replaceChildren();
  if (verificationStatus && message) verificationStatus.textContent = message;
}

function clearVerificationView() {
  clearVerificationResult(!isAuthorized
    ? runtime.state === 'ready'
      ? 'Sign in with the approved Platform identity provider to verify claims against accessible captured evidence.'
      : 'Claim verification is disabled because the approved identity configuration is not ready.'
    : 'Enter a claim and exact citations from captured text, then submit to compare the quotes with TWI evidence.');
  if (verificationForm) verificationForm.reset();
  const rows = getCitationRows();
  for (const row of rows.slice(1)) row.remove();
  const first = getCitationRows()[0];
  if (first) {
    const jobField = first.querySelector('input[name="citation_job_id"]');
    const quoteField = first.querySelector('textarea[name="citation_quote"]');
    if (jobField) jobField.value = '';
    if (quoteField) quoteField.value = '';
  }
  if (claimIdField) claimIdField.value = 'claim-1';
  if (claimStatementField) claimStatementField.value = '';
  citationRowSequence = 1;
  updateVerificationControls();
}

function addCitationRow() {
  const rows = getCitationRows();
  if (rows.length >= 4 || verifying || !verificationCitations) return;
  citationRowSequence += 1;
  const suffix = citationRowSequence;
  const row = document.createElement('fieldset');
  row.className = 'citation-row';
  row.dataset.citationRow = '';

  const legend = document.createElement('legend');
  legend.textContent = `Citation ${rows.length + 1}`;
  const jobId = document.createElement('input');
  jobId.id = `citation-job-${suffix}`;
  jobId.name = 'citation_job_id';
  jobId.type = 'text';
  jobId.maxLength = 64;
  jobId.pattern = '[A-Za-z0-9._:-]{1,64}';
  jobId.required = true;
  jobId.autocomplete = 'off';
  jobId.placeholder = 'TWI job ID';
  const jobLabel = document.createElement('label');
  jobLabel.htmlFor = jobId.id;
  jobLabel.textContent = 'Captured source job ID';

  const quote = document.createElement('textarea');
  quote.id = `citation-quote-${suffix}`;
  quote.name = 'citation_quote';
  quote.rows = 3;
  quote.minLength = 8;
  quote.maxLength = 350;
  quote.required = true;
  quote.placeholder = 'Paste the exact source passage to check.';
  const quoteLabel = document.createElement('label');
  quoteLabel.htmlFor = quote.id;
  quoteLabel.textContent = 'Exact quote from captured text';

  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'button button-secondary remove-citation';
  remove.textContent = 'Remove citation';
  row.append(legend, jobLabel, jobId, quoteLabel, quote, remove);
  verificationCitations.append(row);
  updateVerificationControls();
}

function renderVerificationResponse(response) {
  if (verificationResult) verificationResult.hidden = false;
  if (verificationStatus) {
    verificationStatus.textContent = response.status === 'all_citations_match_captured_text'
      ? `All ${response.citation_count} submitted citation quote(s) matched captured text across ${response.source_count} source job(s). This does not assess factual truth.`
      : 'One or more submitted citation quotes did not match captured text. This does not assess factual truth.';
  }
  if (verificationMetadata) {
    verificationMetadata.replaceChildren();
    const entries = [
      ['Verification ID', response.verification_id],
      ['Verifier version', response.verifier_version],
      ['Verified at', response.verified_at],
      ['Report SHA-256', response.report_sha256],
      ['Overall citation status', response.status],
      ['Source jobs', String(response.source_count)],
      ['Claims', String(response.claim_count)],
      ['Citations', String(response.citation_count)],
      ['Factual truth assessed', 'No'],
    ];
    for (const [label, value] of entries) {
      const term = document.createElement('dt');
      term.textContent = label;
      const description = document.createElement('dd');
      description.textContent = value;
      verificationMetadata.append(term, description);
    }
  }
  if (verifiedClaims) {
    verifiedClaims.replaceChildren();
    for (const claim of response.claims) {
      const article = document.createElement('article');
      article.className = 'verified-claim';
      const heading = document.createElement('h4');
      heading.textContent = claim.statement;
      const id = document.createElement('p');
      id.textContent = `Claim ID: ${claim.claim_id}`;
      const status = document.createElement('p');
      status.className = claim.citation_status === 'all_citations_match_captured_text' ? 'citation-match' : 'citation-mismatch';
      status.textContent = claim.citation_status === 'all_citations_match_captured_text'
        ? 'All citations matched captured text'
        : claim.citation_status === 'partially_matched_citations'
          ? 'Some citations matched; at least one quote was not found'
          : 'Citation mismatch: submitted quote(s) were not found';
      article.append(heading, id, status);

      for (const citation of claim.citations) {
        const detail = document.createElement('div');
        detail.className = 'citation-result';
        const quoteStatus = document.createElement('p');
        quoteStatus.className = citation.quote_match ? 'citation-match' : 'citation-mismatch';
        quoteStatus.textContent = citation.quote_match ? 'Quote matched captured text' : 'Quote not found in captured text';
        const quote = document.createElement('blockquote');
        quote.textContent = citation.quote;
        const job = document.createElement('p');
        job.textContent = `Captured source job: ${citation.job_id}`;
        const source = document.createElement('p');
        source.append(document.createTextNode('Source: '));
        let sourceUrl;
        try {
          sourceUrl = new URL(citation.source.url);
        } catch {
          sourceUrl = null;
        }
        if (
          sourceUrl
          && ['http:', 'https:'].includes(sourceUrl.protocol)
          && !sourceUrl.username
          && !sourceUrl.password
        ) {
          const hasPrivateUrlTail = Boolean(sourceUrl.search || sourceUrl.hash);
          const safeDisplayUrl = sourceUrl.origin + sourceUrl.pathname;
          if (hasPrivateUrlTail) {
            source.append(document.createTextNode(
              safeDisplayUrl + ' (query and fragment omitted for privacy; direct link unavailable)'
            ));
          } else {
            const link = document.createElement('a');
            link.href = sourceUrl.href;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = safeDisplayUrl;
            source.append(link);
          }
        } else {
          source.append(document.createTextNode('Unavailable: source URL did not pass safe-link validation.'));
        }
        const sourceDetails = document.createElement('p');
        sourceDetails.textContent = `Retrieved at: ${citation.source.retrieved_at} · Media type: ${citation.source.media_type} · Content SHA-256: ${citation.source.content_sha256}`;
        detail.append(quoteStatus, quote, job, source, sourceDetails);
        article.append(detail);
      }
      verifiedClaims.append(article);
    }
  }
}


addCitationButton?.addEventListener('click', addCitationRow);

verificationCitations?.addEventListener('click', (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  const removeButton = target.closest('.remove-citation');
  if (!removeButton || verifying) return;
  const row = removeButton.closest('[data-citation-row]');
  if (!row || getCitationRows().length <= 1) return;
  row.remove();
  updateVerificationControls();
});

verificationForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (verifying) return;
  if (!isAuthorized || runtime.state !== 'ready') {
    clearVerificationResult('Sign in with the approved Platform identity provider before verifying citations.');
    return;
  }
  if (!verificationForm.reportValidity()) return;

  const rows = getCitationRows();
  if (rows.length < 1 || rows.length > 4) {
    clearVerificationResult('Submit between one and four citations.');
    return;
  }
  const citations = rows.map((row) => ({
    job_id: row.querySelector('input[name="citation_job_id"]')?.value.trim() ?? '',
    quote: row.querySelector('textarea[name="citation_quote"]')?.value ?? '',
  }));
  const request = {
    claims: [{
      claim_id: claimIdField?.value.trim() ?? '',
      statement: claimStatementField?.value ?? '',
      citations,
    }],
  };
  const requestSessionEpoch = authSessionEpoch;
  verifying = true;
  clearVerificationResult('Submitting citations to TWI for comparison against accessible captured text. This does not assess factual truth.');
  updateVerificationControls();
  if (verifyClaimButton) verifyClaimButton.textContent = 'Checking citations…';
  try {
    const response = await runtime.apiClient.verifyResearch(request);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    renderVerificationResponse(response);
  } catch (error) {
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    clearVerificationResult(error instanceof Error
      ? error.message
      : 'Citation verification failed. No factual-truth conclusion was produced.');
  } finally {
    verifying = false;
    updateVerificationControls();
    if (verifyClaimButton) verifyClaimButton.textContent = 'Verify citations';
  }
});


function createMonitorIdempotencyKey() {
  if (!globalThis.crypto || typeof globalThis.crypto.randomUUID !== 'function') {
    throw new Error('Secure random generation is unavailable; no monitor request was submitted.');
  }
  return `tinlyt-${globalThis.crypto.randomUUID()}`;
}

function isTerminalMonitorRunStatus(status) {
  return ['succeeded', 'failed', 'cancelled'].includes(status);
}

function updateMonitorControls() {
  const authorized = isAuthorized && runtime.state === 'ready';
  const monitorStatusValue = activeMonitor?.status ?? null;
  if (createMonitorButton) createMonitorButton.disabled = !authorized || monitorBusy || monitorRunPolling;
  if (monitorTargetUrlField) monitorTargetUrlField.disabled = !authorized || monitorBusy || monitorRunPolling;
  if (monitorMaxBytesField) monitorMaxBytesField.disabled = !authorized || monitorBusy || monitorRunPolling;
  if (lookupMonitorButton) lookupMonitorButton.disabled = !authorized || monitorBusy || monitorRunPolling;
  if (monitorIdField) monitorIdField.disabled = !authorized || monitorBusy || monitorRunPolling;
  const canLookupRun = Boolean(activeMonitor && monitorStatusValue !== 'deleted');
  if (lookupMonitorRunButton) lookupMonitorRunButton.disabled = !authorized || monitorBusy || monitorRunPolling || !canLookupRun;
  if (monitorRunIdField) monitorRunIdField.disabled = !authorized || monitorBusy || monitorRunPolling || !canLookupRun;
  const runStillActive = Boolean(activeMonitorRunStatus && !isTerminalMonitorRunStatus(activeMonitorRunStatus));
  if (runMonitorButton) runMonitorButton.disabled = !authorized || monitorBusy || monitorRunPolling || runStillActive || !activeMonitor || monitorStatusValue !== 'active';
  if (pauseMonitorButton) pauseMonitorButton.disabled = !authorized || monitorBusy || !activeMonitor || monitorStatusValue !== 'active';
  if (resumeMonitorButton) resumeMonitorButton.disabled = !authorized || monitorBusy || !activeMonitor || monitorStatusValue !== 'paused';
  if (deleteMonitorButton) deleteMonitorButton.disabled = !authorized || monitorBusy || !activeMonitor || monitorStatusValue === 'deleted';
  if (refreshMonitorRunButton) {
    const refreshable = Boolean(activeMonitor && activeMonitorRunId && !monitorRunPolling && !monitorBusy);
    refreshMonitorRunButton.hidden = !refreshable;
    refreshMonitorRunButton.disabled = !authorized || !refreshable;
  }
}

function clearMonitorRunView() {
  activeMonitorRunId = null;
  activeMonitorRunStatus = null;
  if (monitorRunLookupForm) monitorRunLookupForm.reset();
  if (monitorRunStatus) monitorRunStatus.textContent = 'No run has been requested in this session.';
  if (monitorRunMetadata) monitorRunMetadata.replaceChildren();
  if (refreshMonitorRunButton) {
    refreshMonitorRunButton.hidden = true;
    refreshMonitorRunButton.disabled = true;
  }
}

function clearMonitorView() {
  activeMonitor = null;
  pendingMonitorCreateFingerprint = null;
  pendingMonitorCreateKey = null;
  pendingMonitorRunMonitorId = null;
  pendingMonitorRunKey = null;
  if (monitorCreateForm) monitorCreateForm.reset();
  if (monitorLookupForm) monitorLookupForm.reset();
  if (monitorDetails) monitorDetails.hidden = true;
  if (monitorMetadata) monitorMetadata.replaceChildren();
  clearMonitorRunView();
  if (monitorStatus) monitorStatus.textContent = isAuthorized
    ? 'Create a monitor or enter an existing monitor ID. Target URLs are not returned by the API.'
    : runtime.state === 'ready'
      ? 'Sign in with the approved Platform identity provider to create or inspect tenant-scoped monitors.'
      : 'Monitor operations are disabled because the approved identity configuration is not ready.';
  updateMonitorControls();
}

function renderMonitor(monitor, message) {
  if (activeMonitor && activeMonitor.monitor_id !== monitor.monitor_id) {
    pendingMonitorRunMonitorId = null;
    pendingMonitorRunKey = null;
  }
  if (monitor.status === 'deleted') {
    pendingMonitorRunMonitorId = null;
    pendingMonitorRunKey = null;
  }
  activeMonitor = monitor;
  if (monitorIdField) monitorIdField.value = monitor.monitor_id;
  if (monitorDetails) monitorDetails.hidden = false;
  if (monitorStatus) monitorStatus.textContent = message;
  if (monitorMetadata) {
    monitorMetadata.replaceChildren();
    const entries = [
      ['Monitor ID', monitor.monitor_id],
      ['Status', monitor.status],
      ['Baseline digest', monitor.baseline_digest ?? 'No successful baseline yet'],
      ['Baseline observed at', monitor.baseline_observed_at ?? 'Not established'],
      ['Baseline version', String(monitor.baseline_version)],
      ['Created at', monitor.created_at],
      ['Updated at', monitor.updated_at],
    ];
    for (const [label, value] of entries) {
      appendText(monitorMetadata, 'dt', '', label);
      appendText(monitorMetadata, 'dd', '', value);
    }
  }
  updateMonitorControls();
}

function renderMonitorRun(run) {
  activeMonitorRunStatus = run.status;
  if (monitorRunIdField) monitorRunIdField.value = run.job_id;
  if (monitorRunStatus) {
    if (run.status === 'queued' || run.status === 'running') {
      monitorRunStatus.textContent = `TWI reports that monitor run ${run.job_id} is ${run.status}. No change outcome is assumed until the service returns it.`;
    } else if (run.status === 'failed') {
      monitorRunStatus.textContent = run.error_code
        ? `TWI reports that monitor run ${run.job_id} failed. Error code: ${run.error_code}.`
        : `TWI reports that monitor run ${run.job_id} failed. Detailed diagnostics are not available in this response.`;
    } else if (run.status === 'cancelled') {
      monitorRunStatus.textContent = `TWI reports that monitor run ${run.job_id} was cancelled.`;
    } else if (!run.result) {
      monitorRunStatus.textContent = `TWI reports that monitor run ${run.job_id} succeeded without a result payload. No change outcome is assumed.`;
    } else {
      const outcome = run.result.outcome;
      const messages = {
        baseline_established: 'TWI established the first successful content-digest baseline.',
        changed: 'TWI observed a content-digest change since the previous successful baseline.',
        unchanged: 'TWI observed no content-digest change since the previous successful baseline.',
        stale_capture: 'TWI marked this capture as stale and did not apply it to the baseline.',
      };
      monitorRunStatus.textContent = (messages[outcome] ?? 'TWI returned a monitor run outcome.')
        + ' A digest change is an observation, not a truth judgment.';
    }
  }
  if (monitorRunMetadata) {
    monitorRunMetadata.replaceChildren();
    const entries = [
      ['Run ID', run.job_id],
      ['State', run.status],
      ['Attempts', `${run.attempts} / ${run.max_attempts}`],
      ['Error code', run.error_code ?? 'None reported'],
    ];
    if (run.result) {
      entries.push(['Outcome', String(run.result.outcome ?? 'Unknown')]);
      if (typeof run.result.changed === 'boolean' || run.result.changed === null) {
        entries.push(['Digest changed', run.result.changed === null ? 'Not applicable (first baseline or stale capture)' : run.result.changed ? 'Yes' : 'No']);
      }
      if (typeof run.result.changed_units === 'number') entries.push(['Changed units', String(run.result.changed_units)]);
      if (typeof run.result.observed_at === 'string') entries.push(['Observed at', run.result.observed_at]);
      if (typeof run.result.previous_digest === 'string') entries.push(['Previous digest', run.result.previous_digest]);
      if (typeof run.result.current_digest === 'string') entries.push(['Current digest', run.result.current_digest]);
      if (typeof run.result.artifact_id === 'string') entries.push(['Artifact ID', run.result.artifact_id]);
    }
    for (const [label, value] of entries) {
      appendText(monitorRunMetadata, 'dt', '', label);
      appendText(monitorRunMetadata, 'dd', '', value);
    }
  }
  if (refreshMonitorRunButton) {
    const refreshable = !isTerminalMonitorRunStatus(run.status);
    refreshMonitorRunButton.hidden = !refreshable;
    refreshMonitorRunButton.disabled = !isAuthorized || !refreshable || monitorRunPolling || monitorBusy;
  }
  updateMonitorControls();
}

async function refreshMonitorRun(requestSessionEpoch = authSessionEpoch, monitorId = activeMonitor?.monitor_id, runId = activeMonitorRunId) {
  if (!isAuthorized || runtime.state !== 'ready' || !monitorId || !runId || !activeMonitor || activeMonitor.monitor_id !== monitorId) return null;
  try {
    const run = await runtime.apiClient.getMonitorRun(monitorId, runId);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeMonitor?.monitor_id !== monitorId || activeMonitorRunId !== runId) return null;
    renderMonitorRun(run);
    if (run.status === 'succeeded' && isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId) {
      try {
        const refreshedMonitor = await runtime.apiClient.getMonitor(monitorId);
        if (isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId) {
          renderMonitor(refreshedMonitor, 'Monitor state refreshed after the run. The baseline shown is the latest server-reported state.');
        }
      } catch {
        if (isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId && monitorStatus) {
          monitorStatus.textContent = 'The run state is available, but the latest monitor baseline could not be refreshed.';
        }
      }
    }
    return run;
  } catch (error) {
    if (isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId && activeMonitorRunId === runId && monitorRunStatus) {
      monitorRunStatus.textContent = error instanceof Error
        ? error.message
        : 'The monitor run state could not be retrieved. The run may still be active.';
      if (refreshMonitorRunButton) {
        refreshMonitorRunButton.hidden = false;
        refreshMonitorRunButton.disabled = false;
      }
    }
    return null;
  }
}

async function pollMonitorRun(initialRun, requestSessionEpoch, monitorId) {
  if (monitorRunPolling || !activeMonitorRunId || initialRun.job_id !== activeMonitorRunId) return;
  monitorRunPolling = true;
  updateMonitorControls();
  let run = initialRun;
  try {
    for (let attempt = 0; attempt < 20 && !isTerminalMonitorRunStatus(run.status); attempt += 1) {
      await wait(1500);
      if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeMonitor?.monitor_id !== monitorId || activeMonitorRunId !== run.job_id) return;
      const updated = await refreshMonitorRun(requestSessionEpoch, monitorId, run.job_id);
      if (!updated) return;
      run = updated;
    }
    if (!isTerminalMonitorRunStatus(run.status) && monitorRunStatus) {
      monitorRunStatus.textContent = 'The monitor run is still active. Refresh status to request the latest service-reported state; no completion outcome is assumed.';
      if (refreshMonitorRunButton) refreshMonitorRunButton.hidden = false;
    }
  } finally {
    monitorRunPolling = false;
    updateMonitorControls();
  }
}

monitorCreateForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (monitorBusy || !isAuthorized || runtime.state !== 'ready') {
    if (monitorStatus) monitorStatus.textContent = 'Sign in with the approved Platform identity provider before creating a monitor.';
    return;
  }
  if (!monitorCreateForm.reportValidity()) return;
  const targetUrl = monitorTargetUrlField?.value ?? '';
  const maxBytesText = monitorMaxBytesField?.value.trim() ?? '';
  const request = { target_url: targetUrl };
  if (maxBytesText) {
    const maxBytes = Number(maxBytesText);
    if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) {
      if (monitorStatus) monitorStatus.textContent = 'Maximum response bytes must be a positive whole number.';
      return;
    }
    request.policy = { max_bytes: maxBytes };
  }
  const fingerprint = JSON.stringify(request);
  if (pendingMonitorCreateFingerprint !== fingerprint || !pendingMonitorCreateKey) {
    pendingMonitorCreateFingerprint = fingerprint;
    pendingMonitorCreateKey = null;
  }
  monitorBusy = true;
  const requestSessionEpoch = authSessionEpoch;
  updateMonitorControls();
  if (monitorStatus) monitorStatus.textContent = 'Creating the tenant-scoped monitor. TWI will not echo the target URL.';
  let created = null;
  try {
    pendingMonitorCreateKey ??= createMonitorIdempotencyKey();
    created = await runtime.apiClient.createMonitor(request, pendingMonitorCreateKey);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    pendingMonitorCreateFingerprint = null;
    pendingMonitorCreateKey = null;
    clearMonitorRunView();
    renderMonitor(created, 'Monitor created. Save its ID to load it again; the current API does not provide a monitor-list endpoint.');
    if (monitorTargetUrlField) monitorTargetUrlField.value = '';
    if (monitorMaxBytesField) monitorMaxBytesField.value = '';
  } catch (error) {
    if (isAuthorized && authSessionEpoch === requestSessionEpoch && monitorStatus) {
      monitorStatus.textContent = error instanceof Error
        ? error.message
        : 'Monitor creation failed. No monitor is assumed to have been created.';
    }
  } finally {
    monitorBusy = false;
    updateMonitorControls();
  }
});

monitorLookupForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (monitorBusy || monitorRunPolling || !isAuthorized || runtime.state !== 'ready') {
    if (monitorStatus) monitorStatus.textContent = 'Sign in with the approved Platform identity provider before loading a monitor.';
    return;
  }
  if (!monitorLookupForm.reportValidity()) return;
  const requestedId = monitorIdField?.value.trim() ?? '';
  if (!/^[A-Za-z0-9._:-]{1,128}$/.test(requestedId)) {
    if (monitorStatus) monitorStatus.textContent = 'Enter a valid monitor ID.';
    return;
  }
  monitorBusy = true;
  const requestSessionEpoch = authSessionEpoch;
  updateMonitorControls();
  if (monitorStatus) monitorStatus.textContent = 'Requesting the current monitor state from TWI. Tenant and subject access are enforced by the API.';
  try {
    const monitor = await runtime.apiClient.getMonitor(requestedId);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    clearMonitorRunView();
    renderMonitor(monitor, 'Monitor state returned by TWI. Target URL and query values are not displayed.');
  } catch (error) {
    if (isAuthorized && authSessionEpoch === requestSessionEpoch && monitorStatus) {
      monitorStatus.textContent = error instanceof Error
        ? error.message
        : 'The monitor could not be retrieved. No monitor is assumed to be accessible.';
    }
  } finally {
    monitorBusy = false;
    updateMonitorControls();
  }
});

runMonitorButton?.addEventListener('click', async () => {
  const monitorId = activeMonitor?.monitor_id;
  if (!monitorId || activeMonitor?.status !== 'active' || monitorBusy || monitorRunPolling || !isAuthorized || runtime.state !== 'ready') return;
  monitorBusy = true;
  const requestSessionEpoch = authSessionEpoch;
  updateMonitorControls();
  if (monitorRunStatus) monitorRunStatus.textContent = 'Enqueuing one explicit monitor run. No recurring schedule is created.';
  let run = null;
  try {
    if (pendingMonitorRunMonitorId !== monitorId || !pendingMonitorRunKey) {
      pendingMonitorRunMonitorId = monitorId;
      pendingMonitorRunKey = createMonitorIdempotencyKey();
    }
    run = await runtime.apiClient.runMonitor(monitorId, pendingMonitorRunKey);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeMonitor?.monitor_id !== monitorId) return;
    pendingMonitorRunMonitorId = null;
    pendingMonitorRunKey = null;
    activeMonitorRunId = run.job_id;
    renderMonitorRun(run);
  } catch (error) {
    if (isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId && monitorRunStatus) {
      monitorRunStatus.textContent = error instanceof Error
        ? error.message
        : 'The monitor run could not be enqueued. No run outcome is assumed.';
    }
  } finally {
    monitorBusy = false;
    updateMonitorControls();
  }
  if (run && isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId && activeMonitorRunId === run.job_id && !isTerminalMonitorRunStatus(run.status)) {
    await pollMonitorRun(run, requestSessionEpoch, monitorId);
  }
});

refreshMonitorRunButton?.addEventListener('click', async () => {
  if (monitorRunPolling || monitorBusy) return;
  const requestSessionEpoch = authSessionEpoch;
  const monitorId = activeMonitor?.monitor_id;
  const runId = activeMonitorRunId;
  if (!monitorId || !runId || !isAuthorized) return;
  monitorBusy = true;
  updateMonitorControls();
  try {
    await refreshMonitorRun(requestSessionEpoch, monitorId, runId);
  } finally {
    monitorBusy = false;
    updateMonitorControls();
  }
});


monitorRunLookupForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (monitorBusy || monitorRunPolling || !isAuthorized || runtime.state !== 'ready' || !activeMonitor || activeMonitor.status === 'deleted') {
    if (monitorRunStatus) monitorRunStatus.textContent = 'Load an active or paused monitor before looking up its run history.';
    return;
  }
  if (!monitorRunLookupForm.reportValidity()) return;
  const requestedRunId = monitorRunIdField?.value.trim() ?? '';
  if (!/^[A-Za-z0-9._:-]{1,64}$/.test(requestedRunId)) {
    if (monitorRunStatus) monitorRunStatus.textContent = 'Enter a valid monitor run ID.';
    return;
  }
  const monitorId = activeMonitor.monitor_id;
  const requestSessionEpoch = authSessionEpoch;
  monitorBusy = true;
  updateMonitorControls();
  if (monitorRunStatus) monitorRunStatus.textContent = 'Requesting this run from TWI within the currently loaded monitor scope.';
  let run = null;
  try {
    run = await runtime.apiClient.getMonitorRun(monitorId, requestedRunId);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeMonitor?.monitor_id !== monitorId) return;
    activeMonitorRunId = run.job_id;
    renderMonitorRun(run);
  } catch (error) {
    if (isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId && monitorRunStatus) {
      monitorRunStatus.textContent = error instanceof Error
        ? error.message
        : 'The monitor run could not be retrieved. No run state is assumed.';
    }
  } finally {
    monitorBusy = false;
    updateMonitorControls();
  }
  if (!run || !isAuthorized || authSessionEpoch !== requestSessionEpoch || activeMonitor?.monitor_id !== monitorId) return;
  if (!isTerminalMonitorRunStatus(run.status)) {
    await pollMonitorRun(run, requestSessionEpoch, monitorId);
  } else if (run.status === 'succeeded') {
    await refreshMonitorRun(requestSessionEpoch, monitorId, run.job_id);
  }
});

async function changeMonitorStatus(action) {
  const monitorId = activeMonitor?.monitor_id;
  if (!monitorId || monitorBusy || !isAuthorized || runtime.state !== 'ready') return;
  if (action === 'pause' && activeMonitor.status !== 'active') return;
  if (action === 'resume' && activeMonitor.status !== 'paused') return;
  monitorBusy = true;
  const requestSessionEpoch = authSessionEpoch;
  updateMonitorControls();
  if (monitorStatus) monitorStatus.textContent = action === 'pause'
    ? 'Requesting that TWI pause future monitor runs. Already accepted work may finish.'
    : 'Requesting that TWI resume explicit monitor runs.';
  try {
    const monitor = action === 'pause'
      ? await runtime.apiClient.pauseMonitor(monitorId)
      : await runtime.apiClient.resumeMonitor(monitorId);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeMonitor?.monitor_id !== monitorId) return;
    renderMonitor(monitor, action === 'pause'
      ? 'Monitor paused. Already accepted work may finish.'
      : 'Monitor resumed. Runs still require an explicit request.');
  } catch (error) {
    if (isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId && monitorStatus) {
      monitorStatus.textContent = error instanceof Error ? error.message : 'The monitor state could not be changed.';
    }
  } finally {
    monitorBusy = false;
    updateMonitorControls();
  }
}

pauseMonitorButton?.addEventListener('click', () => { void changeMonitorStatus('pause'); });
resumeMonitorButton?.addEventListener('click', () => { void changeMonitorStatus('resume'); });

deleteMonitorButton?.addEventListener('click', async () => {
  const monitorId = activeMonitor?.monitor_id;
  if (!monitorId || activeMonitor.status === 'deleted' || monitorBusy || !isAuthorized || runtime.state !== 'ready') return;
  if (!window.confirm('Delete this monitor and redact its stored target, policy, and run summaries? An already accepted worker lease may finish; deletion does not cancel in-progress work.')) return;
  monitorBusy = true;
  const requestSessionEpoch = authSessionEpoch;
  updateMonitorControls();
  if (monitorStatus) monitorStatus.textContent = 'Requesting monitor deletion and redaction from TWI.';
  try {
    const monitor = await runtime.apiClient.deleteMonitor(monitorId);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeMonitor?.monitor_id !== monitorId) return;
    clearMonitorRunView();
    renderMonitor(monitor, 'Monitor deleted. TWI redacts its stored target and run summaries; an already accepted worker lease may finish.');
  } catch (error) {
    if (isAuthorized && authSessionEpoch === requestSessionEpoch && activeMonitor?.monitor_id === monitorId && monitorStatus) {
      monitorStatus.textContent = error instanceof Error ? error.message : 'Monitor deletion failed; the current server state is not assumed to have changed.';
    }
  } finally {
    monitorBusy = false;
    updateMonitorControls();
  }
});

function showJob(job, message) {
  if (currentEvidenceJobId && currentEvidenceJobId !== job.job_id) clearEvidenceView();
  latestJob = job;
  if (exportEvidenceButton) {
    const exportable = isAuthorized && job.kind === 'fetch' && job.status === 'succeeded' && job.result !== null;
    exportEvidenceButton.hidden = !exportable;
    exportEvidenceButton.disabled = !exportable || exportingEvidence;
  }
  if (!statusPanel) return;
  statusPanel.hidden = false;
  if (statusBadge) statusBadge.textContent = job.status;
  if (statusMessage) {
    const stateMessages = {
      queued: 'TWI reports that this job is queued.',
      running: 'TWI reports that this job is running.',
      succeeded: job.result === null
        ? 'TWI reports success but returned no result payload.'
        : 'TWI reports success. Acquisition success does not establish factual truth.',
      failed: job.error_code
        ? 'TWI reports that this job failed. Error code: ' + job.error_code
        : 'TWI reports that this job failed. Detailed diagnostics are not available in this response.',
      cancelled: 'TWI reports that this job was cancelled.',
    };
    statusMessage.textContent = isTerminalJobStatus(job.status)
      ? stateMessages[job.status]
      : job.cancel_requested
        ? 'TWI reports that cancellation was requested; the job remains ' + job.status + '.'
        : message;
  }
  if (cancelJobButton) {
    const cancellable = isAuthorized && Boolean(activeJobId) && !isTerminalJobStatus(job.status);
    cancelJobButton.hidden = !cancellable;
    cancelJobButton.disabled = !cancellable || job.cancel_requested || cancelling;
    cancelJobButton.textContent = job.cancel_requested ? 'Cancellation requested' : 'Request cancellation';
  }
  if (metadataList) {
    metadataList.replaceChildren();
    const entries = [
      ['Job ID', job.job_id],
      ['Operation', job.kind],
      ['Created', job.created_at],
      ['Last updated', job.updated_at],
      ['Attempts', String(job.attempts) + ' / ' + String(job.max_attempts)],
      ['Cancellation requested', job.cancel_requested ? 'Yes' : 'No'],
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
  if (resultContainer && hasResult) renderJobResult(job);
  else if (resultContainer) resultContainer.replaceChildren();
  if (refreshButton) refreshButton.hidden = isTerminalJobStatus(job.status);
}

function wait(milliseconds) {
  return new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds));
}

async function refreshJob(showProgress = true) {
  const requestedJobId = activeJobId;
  const requestSessionEpoch = authSessionEpoch;
  if (!requestedJobId || runtime.state !== 'ready' || !isAuthorized) return;
  // Do not let a GET already in the polling loop overwrite the state returned by a cancellation POST.
  if (cancelling) return latestJob;
  try {
    const job = await runtime.apiClient.getJob(requestedJobId);
    // Discard results from an earlier session or an old job selection.
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeJobId !== requestedJobId) return null;
    // A request that started before cancellation must not overwrite the newer cancellation response.
    if (cancelling) return latestJob;
    showJob(job, 'Current job state returned by TWI.');
    return job;
  } catch {
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeJobId !== requestedJobId) return null;
    if (cancelling) return latestJob;
    if (statusMessage) statusMessage.textContent = 'The latest job state could not be retrieved. Check the connection and retry; the existing job may still be running.';
    if (refreshButton) refreshButton.hidden = false;
    return null;
  }
}

async function pollJob(initialJob) {
  if (polling) return;
  polling = true;
  if (refreshButton) refreshButton.disabled = true;
  let job = initialJob;
  try {
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
  } finally {
    polling = false;
    if (refreshButton) refreshButton.disabled = !isAuthorized || cancelling;
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
  activeJobId = null;
  latestJob = null;
  clearEvidenceView();
  if (exportEvidenceButton) {
    exportEvidenceButton.hidden = true;
    exportEvidenceButton.disabled = true;
  }
  const requestSessionEpoch = authSessionEpoch;
  submitButton.disabled = true;
  if (lookupButton) lookupButton.disabled = true;
  submitButton.textContent = 'Submitting…';
  if (statusPanel) statusPanel.hidden = false;
  if (statusBadge) statusBadge.textContent = 'Submitting';
  if (statusMessage) statusMessage.textContent = 'Sending the request to TWI. No result is assumed until the service returns it.';
  if (metadataList) metadataList.replaceChildren();
  if (resultWrap) resultWrap.hidden = true;
  if (refreshButton) refreshButton.hidden = true;
  try {
    const job = await runtime.apiClient.createJob(request);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
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
      const arrow = document.createElement('span');
      arrow.setAttribute('aria-hidden', 'true');
      arrow.textContent = '→';
      submitButton.replaceChildren(document.createTextNode('Start investigation '), arrow);
    }
    if (lookupButton) lookupButton.disabled = !isAuthorized;
  }
});

refreshButton?.addEventListener('click', () => { void refreshJob(); });
runLookupForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (submitting || !isAuthorized || runtime.state !== 'ready') return;
  const requestedId = runIdField?.value.trim() ?? '';
  if (!/^[A-Za-z0-9._:-]{1,128}$/.test(requestedId)) {
    if (statusPanel) statusPanel.hidden = false;
    if (statusBadge) statusBadge.textContent = 'Invalid job ID';
    if (statusMessage) statusMessage.textContent = 'Enter a valid TWI job ID using letters, numbers, dot, underscore, colon, or hyphen.';
    return;
  }
  submitting = true;
  clearEvidenceView();
  latestJob = null;
  if (exportEvidenceButton) {
    exportEvidenceButton.hidden = true;
    exportEvidenceButton.disabled = true;
  }
  const requestSessionEpoch = authSessionEpoch;
  if (lookupButton) lookupButton.disabled = true;
  if (submitButton) submitButton.disabled = true;
  if (statusPanel) statusPanel.hidden = false;
  if (statusBadge) statusBadge.textContent = 'Loading run';
  if (statusMessage) statusMessage.textContent = 'Requesting the current job state from TWI. Tenant and subject access are enforced by the API.';
  if (metadataList) metadataList.replaceChildren();
  if (resultWrap) resultWrap.hidden = true;
  if (refreshButton) refreshButton.hidden = true;
  if (cancelJobButton) cancelJobButton.hidden = true;
  activeJobId = null;
  try {
    const job = await runtime.apiClient.getJob(requestedId);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    activeJobId = job.job_id;
    showJob(job, 'Current job state returned by TWI.');
    await pollJob(job);
  } catch (error) {
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    activeJobId = null;
    if (statusBadge) statusBadge.textContent = 'Run lookup failed';
    if (statusMessage) statusMessage.textContent = error instanceof Error
      ? error.message
      : 'The run could not be retrieved. The API did not return an accessible job.';
    if (refreshButton) refreshButton.hidden = true;
    if (cancelJobButton) cancelJobButton.hidden = true;
  } finally {
    submitting = false;
    if (lookupButton) lookupButton.disabled = !isAuthorized;
    if (submitButton) submitButton.disabled = !isAuthorized;
  }
});

exportEvidenceButton?.addEventListener('click', async () => {
  const requestedJobId = activeJobId;
  const requestSessionEpoch = authSessionEpoch;
  if (
    !requestedJobId
    || !isAuthorized
    || exportingEvidence
    || !latestJob
    || latestJob.job_id !== requestedJobId
    || latestJob.kind !== 'fetch'
    || latestJob.status !== 'succeeded'
    || latestJob.result === null
    || runtime.state !== 'ready'
  ) return;

  exportingEvidence = true;
  exportEvidenceButton.disabled = true;
  clearEvidenceView();
  if (evidencePanel) evidencePanel.hidden = false;
  if (evidenceStatus) evidenceStatus.textContent = 'Requesting the tenant-scoped evidence package from TWI and validating its content digest.';
  try {
    const exported = await runtime.apiClient.exportEvidencePackage(requestedJobId);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch || activeJobId !== requestedJobId || !latestJob || latestJob.job_id !== requestedJobId) return;
    renderEvidencePackage(requestedJobId, exported.evidence, exported.bytes);
  } catch (error) {
    if (isAuthorized && authSessionEpoch === requestSessionEpoch && activeJobId === requestedJobId && evidenceStatus) {
      evidenceStatus.textContent = error instanceof Error
        ? error.message
        : 'The evidence package could not be retrieved or validated. No download is available.';
      if (evidencePanel) evidencePanel.hidden = false;
    }
  } finally {
    exportingEvidence = false;
    if (authSessionEpoch === requestSessionEpoch && activeJobId !== requestedJobId) clearEvidenceView();
    if (exportEvidenceButton && latestJob && activeJobId === latestJob.job_id) {
      const exportable = isAuthorized && latestJob.kind === 'fetch' && latestJob.status === 'succeeded' && latestJob.result !== null;
      exportEvidenceButton.hidden = !exportable;
      exportEvidenceButton.disabled = !exportable;
    }
  }
});

downloadEvidenceButton?.addEventListener('click', downloadExactEvidencePackage);

cancelJobButton?.addEventListener('click', async () => {
  if (!activeJobId || !isAuthorized || cancelling || runtime.state !== 'ready') return;
  if (!window.confirm('Request cancellation for this TWI job? A running acquisition may finish its bounded operation before TWI confirms cancellation.')) return;
  const requestSessionEpoch = authSessionEpoch;
  cancelling = true;
  cancelJobButton.disabled = true;
  if (refreshButton) refreshButton.disabled = true;
  if (submitButton) submitButton.disabled = true;
  if (lookupButton) lookupButton.disabled = true;
  if (statusMessage) statusMessage.textContent = 'Sending cancellation request to TWI. Cancellation is not complete until the service reports a terminal cancelled state.';
  try {
    const job = await runtime.apiClient.cancelJob(activeJobId);
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    showJob(job, job.cancel_requested
      ? 'TWI accepted the cancellation request; waiting for a terminal state.'
      : 'TWI returned the current state after the cancellation request.');
    if (!isTerminalJobStatus(job.status)) await pollJob(job);
  } catch (error) {
    if (!isAuthorized || authSessionEpoch !== requestSessionEpoch) return;
    if (statusMessage) statusMessage.textContent = error instanceof Error
      ? error.message
      : 'Cancellation could not be requested. The service-reported job state has not been changed in the interface.';
    if (cancelJobButton) cancelJobButton.disabled = false;
  } finally {
    cancelling = false;
    if (refreshButton) refreshButton.disabled = !isAuthorized || polling;
    if (!submitting) {
      if (submitButton) submitButton.disabled = !isAuthorized;
      if (lookupButton) lookupButton.disabled = !isAuthorized;
    }
    if (cancelJobButton && latestJob && activeJobId && isAuthorized && !isTerminalJobStatus(latestJob.status)) {
      cancelJobButton.hidden = false;
      cancelJobButton.disabled = latestJob.cancel_requested;
    }
  }
});


usageForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!isAuthorized || !usageForm?.reportValidity()) return;
  const query = {
    dimension: usageDimensionField?.value ?? '',
    period_start: usagePeriodField?.value ?? '',
    limit: Number(usageLimitField?.value ?? 100),
    ...(usageCursorField?.value ? { cursor: usageCursorField.value } : {}),
  };
  latestUsageQuery = { dimension: query.dimension, period_start: query.period_start, limit: query.limit };
  latestUsageCursor = null;
  await loadUsage(query, false);
});

loadNextUsagePageButton?.addEventListener('click', async () => {
  if (!latestUsageQuery || !latestUsageCursor || !isAuthorized || usageLoading) return;
  await loadUsage({ ...latestUsageQuery, cursor: latestUsageCursor }, true);
});

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
