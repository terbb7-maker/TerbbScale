let publisherPromise = null;

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.target !== "offscreen") return false;
  if (message.type === "OFFSCREEN_PING") {
    sendResponse({ ok: true, data: { ready: true } });
    return false;
  }
  if (message.type !== "OFFSCREEN_PUBLISH_STORY") return false;
  getPublisher()
    .then(({ publishStoryFromDelivery }) => publishStoryFromDelivery(
      message.payload?.delivery,
      message.payload?.instagramContext,
    ))
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) => sendResponse({
      ok: false,
      error: error instanceof Error ? error.message : "Não foi possível renderizar o Story.",
    }));
  return true;
});

function getPublisher() {
  if (!publisherPromise) {
    publisherPromise = import("./story-publisher.js").catch((error) => {
      publisherPromise = null;
      throw error;
    });
  }
  return publisherPromise;
}
