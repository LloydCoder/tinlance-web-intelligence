import { getRuntime } from "./app/runtime.js";

const activeLinks = document.querySelectorAll('.nav-link');
for (const link of activeLinks) {
  link.addEventListener('click', () => {
    for (const candidate of activeLinks) {
      candidate.classList.remove('is-active');
      candidate.removeAttribute('aria-current');
    }
    link.classList.add('is-active');
    link.setAttribute('aria-current', 'page');
  });
}

const runtimeConfig = window.TINLYT_RUNTIME_CONFIG;
const runtime = getRuntime(runtimeConfig);
const signInButton = document.querySelector('#sign-in');
const modeTitle = document.querySelector('#mode-title');
const modeDescription = document.querySelector('#mode-description');

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
  if (typeof runtimeConfig?.oauth?.redirectUri === 'string') {
    callbackPath = new URL(runtimeConfig.oauth.redirectUri).pathname;
  }
} catch {
  callbackPath = null;
}

if (signInButton && runtime.state === 'ready') {
  signInButton.disabled = false;
  signInButton.textContent = 'Sign in';
  signInButton.setAttribute('aria-label', 'Sign in to Tinlyt');
  signInButton.addEventListener('click', async () => {
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
    if (signInButton) {
      signInButton.disabled = true;
      signInButton.textContent = 'Signed in';
      signInButton.setAttribute('aria-label', 'Signed in; account menu is not available yet');
    }
    showMode(
      'Identity authorization completed',
      'A short-lived TWI access token is held in memory only. Investigation submission and live data views remain disabled until their product workflows are implemented and verified.',
    );
  }).catch(() => {
    if (signInButton) {
      signInButton.disabled = false;
      signInButton.textContent = 'Sign in';
    }
    showMode('Sign-in failed', 'The configured identity flow did not complete. No investigation or evidence operation was started.');
  });
} else if (hasOAuthResponse) {
  stripOAuthResponseParameters();
  showMode(
    'Sign-in unavailable',
    'The OAuth response could not be processed because the approved deployment configuration or callback route is missing. No API-backed operation was performed.',
  );
}
