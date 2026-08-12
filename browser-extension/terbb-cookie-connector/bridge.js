const WEB_SOURCE = "terbb-scale-web";
const EXTENSION_SOURCE = "terbb-scale-extension";
const ALLOWED_COMMANDS = new Set([
  "PING",
  "QUEUE_IMPORT",
  "QUEUE_STATUS",
  "QUEUE_CLEAR",
  "ACTIVATE_CURRENT",
  "OPEN_INVITES",
  "PUBLISH_STORY",
  "NEXT_ACCOUNT",
]);

window.addEventListener("message", (event) => {
  if (
    event.source !== window
    || event.origin !== window.location.origin
    || event.data?.source !== WEB_SOURCE
    || event.data?.version !== 1
    || typeof event.data?.requestId !== "string"
    || !ALLOWED_COMMANDS.has(event.data?.type)
  ) return;

  const { requestId, type, payload } = event.data;
  chrome.runtime.sendMessage({ type, payload }, (response) => {
    const runtimeError = chrome.runtime.lastError;
    window.postMessage({
      source: EXTENSION_SOURCE,
      requestId,
      ok: !runtimeError && response?.ok === true,
      data: response?.data,
      error: runtimeError?.message || response?.error,
    }, window.location.origin);
  });
});
