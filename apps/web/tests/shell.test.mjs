import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const html = await readFile(path.join(root, 'index.html'), 'utf8');
const css = await readFile(path.join(root, 'styles.css'), 'utf8');
const investigationCss = await readFile(path.join(root, 'investigation.css'), 'utf8');
const js = await readFile(path.join(root, 'src/main.js'), 'utf8');
const runtimeConfig = await readFile(path.join(root, 'runtime-config.js'), 'utf8');

test('document declares language, viewport, title and skip navigation', () => {
  assert.match(html, /<html lang="en">/);
  assert.match(html, /name="viewport"/);
  assert.match(html, /<title>Tinlyt — Web Intelligence<\/title>/);
  assert.match(html, /class="skip-link" href="#main"/);
});

test('primary navigation and main landmark are labelled', () => {
  assert.match(html, /<aside class="sidebar" aria-label="Primary navigation">/);
  assert.match(html, /<main id="main" tabindex="-1">/);
  assert.match(html, /aria-current="page"/);
});

test('live investigation controls are disabled until authentication completes', () => {
  assert.match(html, /id="investigation-form"/);
  assert.match(html, /id="run-lookup-form"/);
  assert.match(html, /id="run-id"[^>]*disabled/);
  assert.match(html, /id="cancel-job"[^>]*hidden disabled/);
  assert.match(html, /id="submit-investigation"[^>]*disabled/);
  assert.match(html, /id="job-kind"[^>]*disabled/);
  assert.match(html, /id="sign-in"/);
  assert.match(js, /setLiveControlsEnabled\(true\)/);
  assert.match(js, /runtime\.apiClient\.createJob\(request\)/);
});

test('job response uses text rendering and announces status accessibly', () => {
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /id="job-result" class="result-content"/);
  assert.match(js, /safeWebUrl/);
  assert.match(js, /appendSourceLink/);
  assert.match(js, /link\.rel = 'noopener noreferrer'/);
  assert.match(js, /sourceUrl\.search \|\| sourceUrl\.hash/);
  assert.match(js, /query and fragment omitted for privacy/);
  assert.match(js, /const safeDisplayUrl = sourceUrl\.origin \+ sourceUrl\.pathname/);
  assert.match(js, /appendText\(resultContainer, 'pre', 'result-json'/);
  assert.doesNotMatch(js, /innerHTML\s*=\s*serialized/);
});

test('UI states retrieval is not a truth guarantee and does not show fixture metrics', () => {
  assert.match(html, /not an independent verdict about factual truth/);
  assert.match(html, /No fixture data is presented as live activity/);
  assert.match(js, /no completion outcome is assumed/);
  assert.match(js, /TWI reports that this job failed/);
  assert.match(js, /TWI reports that this job was cancelled/);
  assert.match(js, /activeJobId = null/);
  assert.match(js, /runtime\.apiClient\.getJob\(requestedId\)/);
  assert.match(js, /runtime\.apiClient\.cancelJob\(activeJobId\)/);
  assert.match(js, /window\.confirm/);
  assert.match(js, /job\.cancel_requested/);
});

test('styles retain visible focus, responsive behavior and reduced motion', () => {
  assert.match(css, /:focus-visible/);
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(investigationCss, /@media \(max-width: 600px\)/);
  assert.match(investigationCss, /:focus-visible/);
});

test('runtime configuration is loaded before application and contains no credentials', () => {
  assert.ok(html.indexOf('/runtime-config.js') < html.indexOf('/src/main.js'));
  assert.match(runtimeConfig, /authorizationEndpoint:\s*""/);
  assert.match(runtimeConfig, /tokenEndpoint:\s*""/);
  assert.doesNotMatch(runtimeConfig, /client_secret|access_token|refresh_token/i);
  assert.match(js, /getRuntime/);
});

test('API result is bounded before display and polling is bounded', () => {
  assert.match(js, /const limit = 20_000/);
  assert.match(js, /attempt < 20/);
  assert.match(js, /redirect|truth/i);
});


test('run inspection and cooperative cancellation remain tenant-scoped and explicit', () => {
  assert.match(html, /id="run-lookup-form"/);
  assert.match(html, /id="run-id"[^>]*disabled/);
  assert.match(html, /id="cancel-job"[^>]*hidden disabled/);
  assert.match(js, /runtime\.apiClient\.getJob\(requestedId\)/);
  assert.match(js, /runtime\.apiClient\.cancelJob\(activeJobId\)/);
  assert.match(js, /window\.confirm/);
  assert.match(js, /Cancellation is not complete until the service reports a terminal cancelled state/);
  assert.match(js, /if \(polling\) return/);
  assert.match(js, /if \(cancelling\) return latestJob/);
  assert.match(js, /const job = await runtime\.apiClient\.getJob\(requestedJobId\)/);
  assert.match(js, /refreshButton\.disabled = !enabled \|\| polling \|\| cancelling/);
  assert.match(js, /refreshButton\.disabled = !isAuthorized \|\| polling/);
  assert.match(js, /job\.cancel_requested/);
  assert.match(html, /Tenant-scoped/);
});

test('evidence inspector exposes validated provenance and exact-byte export without a truth claim', () => {
  assert.match(html, /id="export-evidence"[^>]*hidden disabled/);
  assert.match(html, /id="evidence" class="panel evidence-panel"/);
  assert.match(html, /id="evidence-status" role="status" aria-live="polite"/);
  assert.match(html, /id="evidence-integrity-badge" class="quiet-badge">Awaiting package/);
  assert.match(js, /evidenceIntegrityBadge\.textContent = 'Digest verified'/);
  assert.match(js, /evidenceIntegrityBadge\.textContent = 'Awaiting package'/);
  assert.match(html, /id="evidence-metadata" class="evidence-metadata"/);
  assert.match(html, /id="download-evidence"[^>]*disabled/);
  assert.match(html, /does not establish source truth or source authority/);
  assert.match(js, /runtime\.apiClient\.exportEvidencePackage\(requestedJobId\)/);
  assert.match(js, /job\.result !== null/);
  assert.match(js, /latestJob\.result === null/);
  assert.match(js, /new Blob\(\[currentEvidenceBytes\]/);
  assert.match(js, /link\.download = `twi-evidence-/);
  assert.match(js, /Requested URL SHA-256/);
  assert.match(js, /Final URL SHA-256/);
  assert.match(js, /source truth and source authority not assessed/);
  assert.match(js, /let authSessionEpoch = 0/);
  assert.match(js, /authSessionEpoch \+= 1/);
  assert.match(js, /authSessionEpoch !== requestSessionEpoch/);
  assert.match(js, /activeJobId = null;\s*latestJob = null/);
  assert.match(js, /!isAuthorized \|\| authSessionEpoch !== requestSessionEpoch \|\| activeJobId !== requestedJobId/);
});


test('claim verification controls are wired to the scoped API and render citation matches as non-truth claims', () => {
  assert.match(html, /id="verification-form"/);
  assert.match(html, /successful fetch or browser job/);
  assert.match(html, /Captured source job ID/);
  assert.match(js, /Captured source job ID/);
  assert.match(html, /id="verification-citations"/);
  assert.match(html, /id="add-citation"[^>]*type="button"/);
  assert.match(html, /id="verify-claim"[^>]*disabled/);
  assert.match(html, /id="verification-status" role="status" aria-live="polite"/);
  assert.match(html, /id="verification-result"[^>]*hidden/);
  assert.match(js, /addCitationButton\?\.addEventListener\('click', addCitationRow\)/);
  assert.match(js, /verificationCitations\?\.addEventListener\('click'/);
  assert.match(js, /verificationForm\?\.addEventListener\('submit'/);
  assert.match(js, /runtime\.apiClient\.verifyResearch\(request\)/);
  assert.match(js, /requestSessionEpoch = authSessionEpoch/);
  assert.match(js, /authSessionEpoch !== requestSessionEpoch/);
  assert.match(js, /rows\.length >= 4/);
  assert.match(js, /This does not assess factual truth/);
  assert.match(js, /Factual truth assessed', 'No'/);
  assert.match(js, /quote\.textContent = citation\.quote/);
  assert.match(js, /link\.rel = 'noopener noreferrer'/);
  assert.doesNotMatch(js, /verificationResult\.innerHTML\s*=/);
});


test('monitor interface exposes only the documented explicit lifecycle and never fabricates a monitor list', () => {
  assert.match(html, /id="monitors" class="panel monitor-panel"/);
  assert.match(html, /id="monitor-create-form"/);
  assert.match(html, /id="monitor-target-url"[^>]*disabled/);
  assert.match(html, /id="monitor-max-bytes"[^>]*disabled/);
  assert.match(html, /id="monitor-id"[^>]*disabled/);
  assert.match(html, /id="monitor-lookup-form"/);
  assert.match(html, /id="monitor-run-lookup-form"/);
  assert.match(html, /id="monitor-run-id"[^>]*maxlength="64"[^>]*disabled/);
  assert.match(html, /id="lookup-monitor-run"[^>]*disabled/);
  assert.match(html, /id="monitor-id"[^>]*maxlength="64" pattern="\[A-Za-z0-9._:-\]\{1,64\}"/);
  assert.match(html, /There is no monitor-list endpoint in the current API/);
  assert.match(html, /recurrence belongs to Agent OS/);
  assert.match(html, /id="run-monitor"[^>]*disabled/);
  assert.match(html, /id="pause-monitor"[^>]*disabled/);
  assert.match(html, /id="resume-monitor"[^>]*disabled/);
  assert.match(html, /id="delete-monitor"[^>]*disabled/);
  assert.match(html, /id="monitor-status" role="status" aria-live="polite"/);
  assert.match(js, /pendingMonitorCreateKey \?\?= createMonitorIdempotencyKey\(\)/);
  assert.match(js, /runtime\.apiClient\.createMonitor\(request, pendingMonitorCreateKey\)/);
  assert.match(js, /runtime\.apiClient\.getMonitor\(requestedId\)/);
  assert.match(js, /runtime\.apiClient\.runMonitor\(monitorId, pendingMonitorRunKey\)/);
  assert.match(js, /runtime\.apiClient\.getMonitorRun\(monitorId, runId\)/);
  assert.match(js, /monitorRunLookupForm\?\.addEventListener\('submit'/);
  assert.match(js, /runtime\.apiClient\.getMonitorRun\(monitorId, requestedRunId\)/);
  assert.match(js, /runtime\.apiClient\.pauseMonitor\(monitorId\)/);
  assert.match(js, /runtime\.apiClient\.resumeMonitor\(monitorId\)/);
  assert.match(js, /runtime\.apiClient\.deleteMonitor\(monitorId\)/);
  assert.match(js, /Captured source job:/);
  assert.match(js, /citation\.job_id/);
  assert.doesNotMatch(js, /Captured fetch job:/);
  assert.match(js, /Delete this monitor and redact its stored target, policy, and run summaries/);
  assert.match(js, /already accepted worker lease may finish/);
  assert.match(js, /authSessionEpoch !== requestSessionEpoch/);
  assert.match(js, /No recurring schedule is created/);
  assert.match(js, /runStillActive = Boolean\(activeMonitorRunStatus && !isTerminalMonitorRunStatus\(activeMonitorRunStatus\)\)/);
  assert.match(js, /Monitor state refreshed after the run/);
  assert.doesNotMatch(js, /localStorage/);
  assert.doesNotMatch(html, /Monitor UI planned/);
});

test('developer reference documents supported contracts without exposing credential controls or sending requests', () => {
  assert.match(html, /id="developer" class="panel developer-panel"/);
  assert.match(html, /id="developer-search-example"/);
  assert.match(html, /id="developer-verify-example"/);
  assert.match(html, /POST \/v1\/jobs/);
  assert.match(html, /twi:research:verify/);
  assert.match(html, /No request is sent from this reference panel/);
  assert.match(html, /Never paste access tokens into this page/);
  assert.match(html, /does not assess factual truth or source authority/);
  assert.match(js, /developerCopyButtons/);
  assert.match(js, /navigator\.clipboard\?\.writeText/);
  assert.match(js, /Clipboard access is unavailable in this context/);
  assert.doesNotMatch(html, /create API key|rotate API key|billing portal/i);
});

test('usage interface is tenant-scoped, cursor-paginated, and excludes unsupported administration controls', () => {
  assert.match(html, /id="usage" class="panel usage-panel"/);
  assert.match(html, /id="usage-form"/);
  assert.match(html, /id="usage-dimension"/);
  assert.match(html, /id="usage-period-start"/);
  assert.match(html, /id="load-next-usage-page"[^>]*type="button" hidden disabled/);
  assert.match(html, /twi:usage:read/);
  assert.match(html, /Tenant and subject are derived by TWI from the verified token/);
  assert.match(html, /not invoice balances/);
  assert.match(html, /Unsupported tenant-administration and credential-management actions are not exposed/);
  assert.match(html, /id="usage-status" role="status" aria-live="polite"/);
  assert.match(js, /runtime\.apiClient\.readUsage\(query\)/);
  assert.match(js, /latestUsageCursor/);
  assert.match(js, /usageForm\?\.addEventListener\('submit'/);
  assert.match(js, /loadNextUsagePageButton\?\.addEventListener\('click'/);
  assert.match(js, /authSessionEpoch !== requestSessionEpoch/);
  assert.match(js, /clearUsageView\(\)/);
  assert.match(js, /event\.event_id/);
  assert.doesNotMatch(js, /localStorage/);
  assert.doesNotMatch(html, /id="(?:tenant-switch|create-api-key|rotate-credentials|invoice-balance)"/i);
});
