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

  let callbackPath = null;
  try {
    callbackPath = new URL(runtimeConfig.oauth.redirectUri).pathname;
  } catch {
    callbackPath = null;
  }
  if (callbackPath && window.location.pathname === callbackPath) {
    runtime.handleCallback().then(() => {
      signInButton.disabled = true;
      signInButton.textContent = 'Signed in';
      signInButton.setAttribute('aria-label', 'Signed in; account menu is not available yet');
      showMode(
        'Identity authorization completed',
        'A short-lived TWI access token is held in memory only. Investigation submission and live data views remain disabled until their product workflows are implemented and verified.',
      );
    }).catch(() => {
      signInButton.disabled = false;
      signInButton.textContent = 'Sign in';
      showMode('Sign-in failed', 'The configured identity flow did not complete. No investigation or evidence operation was started.');
    });
  }
} else if (signInButton) {
  signInButton.disabled = true;
  signInButton.title = runtime.message;
}
