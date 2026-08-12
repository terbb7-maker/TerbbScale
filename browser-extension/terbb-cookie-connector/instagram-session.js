const REQUIRED_HEADERS = [
  "x-asbd-id",
  "x-instagram-ajax",
  "x-ig-app-id",
  "x-web-session-id",
];
const OPTIONAL_HEADERS = ["x-ig-www-claim"];
const HEADER_STORAGE_KEY = "terbb_instagram_headers_v1";
const HEADER_TTL_MS = 7 * 60 * 1000;

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    const captured = {};
    for (const header of details.requestHeaders || []) {
      const name = header.name.toLowerCase();
      if ([...REQUIRED_HEADERS, ...OPTIONAL_HEADERS].includes(name) && header.value && header.value !== "0") {
        captured[name] = header.value;
      }
    }
    if (!Object.keys(captured).length) return;
    chrome.storage.session.get(HEADER_STORAGE_KEY).then((stored) => {
      const previous = stored[HEADER_STORAGE_KEY] || {};
      chrome.storage.session.set({
        [HEADER_STORAGE_KEY]: {
          ...previous,
          ...captured,
          capturedAt: Date.now(),
        },
      });
    });
  },
  { urls: ["https://*.instagram.com/*"], types: ["xmlhttprequest", "main_frame", "sub_frame"] },
  ["requestHeaders", "extraHeaders"],
);

async function readInstagramCookies() {
  const names = ["sessionid", "csrftoken", "ds_user_id"];
  const entries = await Promise.all(
    names.map(async (name) => {
      const cookie = await chrome.cookies.get({ url: "https://www.instagram.com/", name });
      return [name, cookie?.value || null];
    }),
  );
  return Object.fromEntries(entries);
}

async function readInstagramHeaders() {
  const stored = await chrome.storage.session.get(HEADER_STORAGE_KEY);
  return stored[HEADER_STORAGE_KEY] || {};
}

export async function requireInstagramContext(expectedAccountId) {
  const cookies = await readInstagramCookies();
  if (!cookies.sessionid || !cookies.csrftoken || !cookies.ds_user_id) {
    throw new Error("A sessão do Instagram está incompleta. Ative a conta novamente.");
  }
  if (String(cookies.ds_user_id) !== String(expectedAccountId)) {
    throw new Error("A sessão ativa não corresponde à conta atual da fila.");
  }

  const headers = await readInstagramHeaders();
  const missing = REQUIRED_HEADERS.filter((name) => !headers[name]);
  const stale = !headers.capturedAt || Date.now() - Number(headers.capturedAt) > HEADER_TTL_MS;
  if (missing.length || stale) {
    throw new Error("Abra o Instagram da conta atual, aguarde o feed carregar e tente novamente.");
  }
  return { cookies, headers };
}

export async function clearInstagramHeaders() {
  await chrome.storage.session.remove(HEADER_STORAGE_KEY);
}
