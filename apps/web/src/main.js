// F1 intentionally ships no live API behavior. Keep the runtime small until
// authentication and the canonical API client are implemented in F2.
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
