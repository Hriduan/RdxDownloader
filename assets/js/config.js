/* Public deployment address, not a secret. Same-origin hosting stays local. */
window.RDX_CONFIG = Object.freeze({
  apiBase: location.hostname === 'hriduan.github.io' ? 'https://rdxdownloader.onrender.com' : '',
  deployedBackend: 'https://rdxdownloader.onrender.com',
  pollIntervalMs: 1500
});
