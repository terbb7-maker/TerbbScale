import {
  clearInstagramHeaders,
  requireInstagramContext,
} from "./instagram-session.js";

const STORAGE_KEY = "terbb_cookie_queue_v1";
const INSTAGRAM_ORIGIN = "https://www.instagram.com";
const INVITES_URL = "https://www.instagram.com/accounts/manage_access/";
const MAX_BATCHES = 200;
const MAX_COOKIES_PER_BATCH = 100;
const OFFSCREEN_READY_ATTEMPTS = 50;
const OFFSCREEN_READY_DELAY_MS = 100;

let offscreenSetupPromise = null;

chrome.runtime.onInstalled.addListener(async () => {
  await chrome.storage.session.setAccessLevel({ accessLevel: "TRUSTED_CONTEXTS" });
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.target === "offscreen") return false;
  handleMessage(message)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) => sendResponse({ ok: false, error: safeError(error) }));
  return true;
});

async function handleMessage(message) {
  switch (message?.type) {
    case "PING":
      return { version: chrome.runtime.getManifest().version };
    case "QUEUE_IMPORT":
      return importQueue(message.payload);
    case "QUEUE_STATUS":
      return publicStatus(await getQueue());
    case "QUEUE_CLEAR":
      await chrome.storage.session.remove(STORAGE_KEY);
      return publicStatus(emptyQueue());
    case "ACTIVATE_CURRENT":
      return activateCurrent();
    case "OPEN_INVITES":
      await chrome.tabs.create({ url: INVITES_URL, active: true });
      return { opened: true };
    case "PUBLISH_STORY":
      return publishCurrentStory(message.payload);
    case "NEXT_ACCOUNT":
      return activateNext();
    default:
      throw new Error("Comando não permitido.");
  }
}

async function importQueue(payload) {
  if (!Array.isArray(payload?.batches) || payload.batches.length === 0) {
    throw new Error("Selecione pelo menos um arquivo de cookies.");
  }
  if (payload.batches.length > MAX_BATCHES) {
    throw new Error(`A fila aceita no máximo ${MAX_BATCHES} contas por vez.`);
  }

  const items = payload.batches.map((batch, index) => sanitizeBatch(batch, index));
  const queue = { items, activeIndex: 0 };
  await chrome.storage.session.set({ [STORAGE_KEY]: queue });
  return publicStatus(queue);
}

function sanitizeBatch(batch, index) {
  if (!batch || !Array.isArray(batch.cookies) || batch.cookies.length > MAX_COOKIES_PER_BATCH) {
    throw new Error(`Arquivo ${index + 1}: lista de cookies inválida.`);
  }

  const cookies = batch.cookies
    .filter((cookie) => isInstagramDomain(cookie?.domain))
    .map(sanitizeCookie);
  const sessionId = cookies.find((cookie) => cookie.name === "sessionid");
  const accountId = cookies.find((cookie) => cookie.name === "ds_user_id");
  if (!sessionId?.value || !accountId?.value) {
    throw new Error(`${cleanFileName(batch.file_name, index)}: sessionid ou ds_user_id ausente.`);
  }

  return {
    id: crypto.randomUUID(),
    fileName: cleanFileName(batch.file_name, index),
    accountHint: maskAccountId(accountId.value),
    cookies,
    accountId: accountId.value,
    story: { status: "idle", publishedLink: null, error: null, publishedAt: null },
  };
}

function sanitizeCookie(cookie) {
  if (typeof cookie.name !== "string" || !cookie.name || cookie.name.length > 128) {
    throw new Error("O arquivo contém um cookie sem nome válido.");
  }
  if (typeof cookie.value !== "string" || cookie.value.length > 16_384) {
    throw new Error(`O cookie ${cookie.name} não possui um valor válido.`);
  }

  const expires = Number(cookie.expires);
  return {
    name: cookie.name,
    value: cookie.value,
    domain: ".instagram.com",
    path: typeof cookie.path === "string" && cookie.path.startsWith("/") ? cookie.path : "/",
    secure: cookie.secure !== false,
    httpOnly: cookie.httpOnly === true,
    sameSite: normalizeSameSite(cookie.sameSite),
    expirationDate: Number.isFinite(expires) && expires > Date.now() / 1000 ? expires : undefined,
  };
}

function isInstagramDomain(domain) {
  if (typeof domain !== "string") return false;
  const normalized = domain.trim().toLowerCase().replace(/^\./, "");
  return normalized === "instagram.com" || normalized.endsWith(".instagram.com");
}

function normalizeSameSite(value) {
  switch (String(value ?? "").toLowerCase()) {
    case "none":
    case "no_restriction":
      return "no_restriction";
    case "strict":
      return "strict";
    case "lax":
      return "lax";
    default:
      return "unspecified";
  }
}

async function activateCurrent() {
  const queue = await getQueue();
  const item = queue.items[queue.activeIndex];
  if (!item) throw new Error("A fila está vazia.");
  await replaceInstagramCookies(item.cookies);
  await clearInstagramHeaders();
  await chrome.tabs.create({ url: `${INSTAGRAM_ORIGIN}/`, active: true });
  return publicStatus(queue);
}

async function activateNext() {
  const queue = await getQueue();
  if (queue.activeIndex + 1 >= queue.items.length) {
    throw new Error("Esta é a última conta da fila.");
  }
  queue.activeIndex += 1;
  await replaceInstagramCookies(queue.items[queue.activeIndex].cookies);
  await clearInstagramHeaders();
  await chrome.storage.session.set({ [STORAGE_KEY]: queue });
  await chrome.tabs.create({ url: `${INSTAGRAM_ORIGIN}/`, active: true });
  return publicStatus(queue);
}

async function publishCurrentStory(payload) {
  const queue = await getQueue();
  const item = queue.items[queue.activeIndex];
  if (!item) throw new Error("A fila está vazia.");
  if (!payload?.delivery) throw new Error("O Story predefinido não foi recebido.");
  if (item.story?.status === "publishing") throw new Error("Já existe um Story em publicação.");

  item.story = { status: "publishing", publishedLink: null, error: null, publishedAt: null };
  await chrome.storage.session.set({ [STORAGE_KEY]: queue });
  try {
    const { cookies, headers } = await requireInstagramContext(item.accountId);
    const rendered = await sendToOffscreen({
      target: "offscreen",
      type: "OFFSCREEN_PUBLISH_STORY",
      payload: {
        delivery: payload.delivery,
        instagramContext: {
          accountId: cookies.ds_user_id,
          csrfToken: cookies.csrftoken,
          appId: headers["x-ig-app-id"],
        },
      },
    });
    if (!rendered?.ok) throw new Error(rendered?.error || "A renderização local do Story falhou.");
    const result = rendered.data;
    item.story = {
      status: "published",
      publishedLink: result.publishedLink || null,
      error: null,
      publishedAt: new Date().toISOString(),
    };
    await chrome.storage.session.set({ [STORAGE_KEY]: queue });
    return {
      status: publicStatus(queue),
      published_link: item.story.publishedLink,
      published_at: item.story.publishedAt,
    };
  } catch (error) {
    item.story = {
      status: "failed",
      publishedLink: null,
      error: safeError(error),
      publishedAt: null,
    };
    await chrome.storage.session.set({ [STORAGE_KEY]: queue });
    throw error;
  }
}

async function ensureOffscreenDocument() {
  if (!chrome.offscreen) throw new Error("Atualize o Chrome para editar Stories em vídeo.");
  if (!offscreenSetupPromise) {
    offscreenSetupPromise = prepareOffscreenDocument().finally(() => {
      offscreenSetupPromise = null;
    });
  }
  return offscreenSetupPromise;
}

async function prepareOffscreenDocument() {
  if (!(await chrome.offscreen.hasDocument())) {
    await createOffscreenDocument();
  }
  if (await waitForOffscreenReady()) return;

  await chrome.offscreen.closeDocument().catch(() => undefined);
  await createOffscreenDocument();
  if (await waitForOffscreenReady()) return;

  throw new Error("O renderizador local do Story não iniciou mesmo após reiniciar. Recarregue a extensão e tente novamente.");
}

async function createOffscreenDocument() {
  await chrome.offscreen.createDocument({
    url: "offscreen.html",
    reasons: ["WORKERS"],
    justification: "Renderizar localmente o adesivo de link em imagens e vídeos do Story.",
  });
}

async function waitForOffscreenReady() {
  for (let attempt = 0; attempt < OFFSCREEN_READY_ATTEMPTS; attempt += 1) {
    try {
      const response = await chrome.runtime.sendMessage({
        target: "offscreen",
        type: "OFFSCREEN_PING",
      });
      if (response?.ok && response.data?.ready === true) return true;
    } catch (error) {
      if (!isMissingReceiverError(error)) throw error;
    }
    await delay(OFFSCREEN_READY_DELAY_MS);
  }
  return false;
}

async function sendToOffscreen(message) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    await ensureOffscreenDocument();
    try {
      return await chrome.runtime.sendMessage(message);
    } catch (error) {
      if (!isMissingReceiverError(error) || attempt === 1) throw error;
      await delay(OFFSCREEN_READY_DELAY_MS);
    }
  }
  throw new Error("O renderizador local do Story não respondeu.");
}

function isMissingReceiverError(error) {
  return String(error instanceof Error ? error.message : error)
    .includes("Receiving end does not exist");
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function replaceInstagramCookies(cookies) {
  const existing = await chrome.cookies.getAll({ domain: "instagram.com" });
  await Promise.all(existing.map(removeCookie));
  for (const cookie of cookies) {
    const details = {
      url: `${INSTAGRAM_ORIGIN}${cookie.path}`,
      name: cookie.name,
      value: cookie.value,
      domain: cookie.domain,
      path: cookie.path,
      secure: cookie.secure,
      httpOnly: cookie.httpOnly,
      sameSite: cookie.sameSite,
    };
    if (cookie.expirationDate) details.expirationDate = cookie.expirationDate;
    const saved = await chrome.cookies.set(details);
    if (!saved) throw new Error(`Não foi possível aplicar o cookie ${cookie.name}.`);
  }
}

async function removeCookie(cookie) {
  const host = cookie.domain.replace(/^\./, "");
  const scheme = cookie.secure ? "https" : "http";
  await chrome.cookies.remove({
    url: `${scheme}://${host}${cookie.path || "/"}`,
    name: cookie.name,
    storeId: cookie.storeId,
  });
}

async function getQueue() {
  const stored = await chrome.storage.session.get(STORAGE_KEY);
  const queue = stored[STORAGE_KEY];
  if (!queue || !Array.isArray(queue.items)) return emptyQueue();
  queue.items = queue.items.map((item) => ({
    ...item,
    accountId: item.accountId || item.cookies?.find((cookie) => cookie.name === "ds_user_id")?.value,
    story: item.story || { status: "idle", publishedLink: null, error: null, publishedAt: null },
  }));
  return queue;
}

function emptyQueue() {
  return { items: [], activeIndex: 0 };
}

function publicStatus(queue) {
  return {
    active_index: queue.activeIndex,
    items: queue.items.map((item) => ({
      id: item.id,
      file_name: item.fileName,
      account_hint: item.accountHint,
      cookie_count: item.cookies.length,
      story_status: item.story?.status || "idle",
      story_link: item.story?.publishedLink || null,
      story_error: item.story?.error || null,
      story_published_at: item.story?.publishedAt || null,
    })),
  };
}

function cleanFileName(value, index) {
  const fallback = `conta-${index + 1}.json`;
  if (typeof value !== "string") return fallback;
  const cleaned = value.replace(/[\\/\u0000-\u001f]/g, "").slice(0, 160).trim();
  return cleaned || fallback;
}

function maskAccountId(value) {
  const text = String(value);
  if (text.length <= 4) return "••••";
  return `••••${text.slice(-4)}`;
}

function safeError(error) {
  const message = error instanceof Error ? error.message : "Falha inesperada na extensão.";
  return message
    .replace(/sessionid=[^\s&]+/gi, "sessionid=[oculto]")
    .replace(/csrftoken=[^\s&]+/gi, "csrftoken=[oculto]")
    .replace(/https:\/\/[^\s]+supabase\.co[^\s]*/gi, "[url-temporaria-oculta]")
    .slice(0, 300);
}
