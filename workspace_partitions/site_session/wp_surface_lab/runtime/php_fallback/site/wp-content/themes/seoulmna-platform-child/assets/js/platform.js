document.addEventListener('click', function (event) {
  var target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  var anchor = target.closest('[data-smna-scroll-target]');
  if (!anchor) {
    return;
  }
  var selector = anchor.getAttribute('data-smna-scroll-target');
  if (!selector) {
    return;
  }
  var next = document.querySelector(selector);
  if (!next) {
    return;
  }
  event.preventDefault();
  next.scrollIntoView({ behavior: 'smooth', block: 'start' });
});
