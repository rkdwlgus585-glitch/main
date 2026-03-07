document.addEventListener('click', function (event) {
  var target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  var button = target.closest('[data-smna-calc-launch="true"]');
  if (!button) {
    return;
  }
  event.preventDefault();
  var mountId = button.getAttribute('data-smna-target');
  var src = button.getAttribute('data-smna-src');
  var title = button.getAttribute('data-smna-title') || 'Calculator';
  if (!mountId || !src) {
    return;
  }
  var mount = document.getElementById(mountId);
  if (!mount) {
    return;
  }
  if (mount.dataset.loaded === 'true') {
    mount.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }
  var iframe = document.createElement('iframe');
  iframe.className = 'smna-calc-gate__frame';
  iframe.src = src;
  iframe.title = title;
  iframe.loading = 'lazy';
  iframe.referrerPolicy = 'strict-origin-when-cross-origin';
  iframe.setAttribute('sandbox', 'allow-scripts allow-forms allow-popups');
  mount.appendChild(iframe);
  mount.dataset.loaded = 'true';
  mount.scrollIntoView({ behavior: 'smooth', block: 'start' });
});
