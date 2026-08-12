import { publishStoryFromDelivery } from "./story-publisher.js";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.target !== "offscreen" || message?.type !== "OFFSCREEN_PUBLISH_STORY") return false;
  publishStoryFromDelivery(message.payload?.delivery, message.payload?.expectedAccountId)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) => sendResponse({
      ok: false,
      error: error instanceof Error ? error.message : "Não foi possível renderizar o Story.",
    }));
  return true;
});
