(() => {
  'use strict';
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const header = document.querySelector('.site-header');
  if (header) {
    const nav = header.querySelector('nav[aria-label="Main navigation"]');
    if (nav) {
      nav.id = nav.id || 'site-primary-navigation';
      const button = make('button', 'site-nav-toggle');
      button.type = 'button';
      button.setAttribute('aria-controls', nav.id);
      button.setAttribute('aria-expanded', 'false');
      button.setAttribute('aria-label', 'Open navigation');
      button.append(make('span', 'site-nav-toggle-label', 'Menu'));
      const icon = make('span', 'site-nav-toggle-icon');
      icon.setAttribute('aria-hidden', 'true');
      icon.append(make('span'), make('span'), make('span'));
      button.append(icon);
      header.insertBefore(button, nav);
      header.dataset.navEnhanced = 'true';
      const close = (restoreFocus = false) => {
        nav.classList.remove('is-open');
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-label', 'Open navigation');
        button.querySelector('.site-nav-toggle-label').textContent = 'Menu';
        if (restoreFocus) button.focus();
      };
      const open = () => {
        nav.classList.add('is-open');
        button.setAttribute('aria-expanded', 'true');
        button.setAttribute('aria-label', 'Close navigation');
        button.querySelector('.site-nav-toggle-label').textContent = 'Close';
      };
      button.addEventListener('click', () => button.getAttribute('aria-expanded') === 'true' ? close() : open());
      nav.addEventListener('click', event => {
        if (event.target instanceof Element && event.target.closest('a')) close();
      });
      document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && button.getAttribute('aria-expanded') === 'true') close(true);
      });
      document.addEventListener('click', event => {
        if (button.getAttribute('aria-expanded') !== 'true') return;
        if (event.target instanceof Node && !header.contains(event.target)) close();
      });
      const desktop = window.matchMedia('(min-width: 901px)');
      const resetAtDesktop = event => { if (event.matches) close(); };
      if (desktop.addEventListener) desktop.addEventListener('change', resetAtDesktop);
      else if (desktop.addListener) desktop.addListener(resetAtDesktop);
    }
  }

  const sidebar = document.querySelector('.app-shell .sidebar');
  const topbar = document.querySelector('.app-shell .topbar');
  if (sidebar && topbar) {
    sidebar.id = sidebar.id || 'workspace-sidebar';
    const toggle = make('button', 'workspace-nav-toggle');
    toggle.type = 'button';
    toggle.setAttribute('aria-controls', sidebar.id);
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open workspace navigation');
    toggle.append(make('span', 'workspace-nav-toggle-icon', '☰'), make('span', '', 'Navigation'));
    const breadcrumb = topbar.querySelector('.breadcrumb');
    topbar.insertBefore(toggle, breadcrumb || topbar.firstChild);
    const closeSidebar = (restoreFocus = false) => {
      sidebar.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open workspace navigation');
      document.body.classList.remove('workspace-nav-open');
      if (restoreFocus) toggle.focus();
    };
    const openSidebar = () => {
      sidebar.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', 'Close workspace navigation');
      document.body.classList.add('workspace-nav-open');
      const firstLink = sidebar.querySelector('nav a[href]');
      if (firstLink) firstLink.focus();
    };
    toggle.addEventListener('click', () => toggle.getAttribute('aria-expanded') === 'true' ? closeSidebar() : openSidebar());
    sidebar.querySelectorAll('nav a[href]').forEach(link => link.addEventListener('click', () => closeSidebar()));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') closeSidebar(true);
    });
    document.addEventListener('click', event => {
      if (toggle.getAttribute('aria-expanded') !== 'true') return;
      if (event.target instanceof Node && !sidebar.contains(event.target) && !toggle.contains(event.target)) closeSidebar();
    });
    const desktop = window.matchMedia('(min-width: 901px)');
    const resetAtDesktop = event => { if (event.matches) closeSidebar(); };
    if (desktop.addEventListener) desktop.addEventListener('change', resetAtDesktop);
    else if (desktop.addListener) desktop.addListener(resetAtDesktop);
  }
})();
