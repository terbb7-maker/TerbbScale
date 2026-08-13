import { compositeVideoOverlay } from "./ffmpeg-runner.js";

const INSTAGRAM_APP_ID = "936619743392459";
const MAX_IMAGE_BYTES = 25 * 1024 * 1024;
const MAX_VIDEO_BYTES = 100 * 1024 * 1024;
const STORY_FONTS = {
  Inter: ["Inter-VariableFont_opsz,wght.woff2", "Inter-Italic-VariableFont_opsz,wght.woff2"],
  Roboto: ["Roboto-VariableFont_wdth,wght.woff2", "Roboto-Italic-VariableFont_wdth,wght.woff2"],
  Poppins: ["Poppins-Regular.woff2", "Poppins-Italic.woff2"],
  Montserrat: ["Montserrat-VariableFont_wght.woff2", "Montserrat-Italic-VariableFont_wght.woff2"],
  "Bebas Neue": ["BebasNeue-Regular.woff2"],
  "Playfair Display": ["PlayfairDisplay-VariableFont_wght.woff2", "PlayfairDisplay-Italic-VariableFont_wght.woff2"],
  Merriweather: ["Merriweather-VariableFont_opsz,wdth,wght.ttf", "Merriweather-Italic-VariableFont_opsz,wdth,wght.woff2"],
  Pacifico: ["Pacifico-Regular.woff2"],
  DancingScript: ["DancingScript-VariableFont_wght.woff2"],
  Anton: ["Anton-Regular.woff2"],
  Lora: ["Lora-VariableFont_wght.woff2", "Lora-Italic-VariableFont_wght.woff2"],
  "Great Vibes": ["GreatVibes-Regular.woff2"],
};
const STORY_COLORS = new Set([
  "#ffffff",
  "rgba(0, 0, 0, 0.6)",
  "rgba(0, 0, 0, 1)",
  "rgba(65, 174, 69, 1)",
  "rgba(0, 212, 255, 1)",
  "rgba(53, 141, 255, 1)",
  "rgba(115, 0, 255, 1)",
  "rgba(255, 255, 255, 1)",
  "rgba(255, 192, 10, 1)",
  "rgba(255, 129, 0, 1)",
  "rgba(255, 49, 49, 1)",
  "rgba(255, 101, 195, 1)",
]);
const loadedFonts = new Map();

export async function publishStoryFromDelivery(delivery, instagramContext) {
  validateDelivery(delivery);
  const context = validateInstagramContext(instagramContext);
  const response = await fetch(delivery.media_url, {
    method: "GET",
    credentials: "omit",
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Não foi possível baixar a mídia temporária do Terbb Scale.");
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength !== Number(delivery.size_bytes)) {
    throw new Error("O tamanho da mídia recebida não corresponde ao arquivo configurado.");
  }

  await ensureStoryFont(delivery.sticker_font_family, delivery.sticker_italic);
  const source = new Blob([bytes], { type: delivery.mime_type });
  const prepared = delivery.media_kind === "image"
    ? await normalizeStoryImage(source, delivery)
    : await renderStoryVideo(source, delivery);
  const uploadId = String(Date.now());
  const entityName = `story_${uploadId}`;

  if (delivery.media_kind === "image") {
    await uploadStoryPhoto(entityName, uploadId, prepared, context.appId);
  } else {
    await uploadStoryVideo(entityName, uploadId, prepared, context.appId);
  }
  const configured = await configureStory(uploadId, delivery, context);
  const media = parseInstagramJson(configured).media;
  const publishedLink = media?.pk
    ? `https://www.instagram.com/stories/${media.user?.username || context.accountId}/${media.pk}/`
    : null;
  return { publishedLink, mediaId: media?.pk ? String(media.pk) : null };
}

function validateInstagramContext(context) {
  if (!context || typeof context !== "object") {
    throw new Error("O contexto local do Instagram não foi recebido.");
  }
  const accountId = String(context.accountId || "");
  const csrfToken = String(context.csrfToken || "");
  const appId = String(context.appId || "");
  if (!/^\d{1,32}$/.test(accountId) || !csrfToken || csrfToken.length > 256 || !/^\d{1,32}$/.test(appId)) {
    throw new Error("O contexto local do Instagram é inválido. Ative a conta novamente.");
  }
  return { accountId, csrfToken, appId };
}

function validateDelivery(delivery) {
  if (!delivery || typeof delivery !== "object") throw new Error("Preset do Story inválido.");
  const mediaUrl = new URL(delivery.media_url);
  const linkUrl = new URL(delivery.link_url);
  if (mediaUrl.protocol !== "https:" || mediaUrl.hostname !== "kctretlyslltvkfydoyy.supabase.co") {
    throw new Error("A origem temporária da mídia não é permitida.");
  }
  if (linkUrl.protocol !== "https:" || linkUrl.username || linkUrl.password) {
    throw new Error("O link do Story precisa ser HTTPS e não pode conter credenciais.");
  }
  if (!Number.isFinite(Date.parse(delivery.expires_at)) || Date.parse(delivery.expires_at) <= Date.now()) {
    throw new Error("A entrega temporária da mídia expirou. Tente novamente.");
  }
  const size = Number(delivery.size_bytes);
  const max = delivery.media_kind === "video" ? MAX_VIDEO_BYTES : MAX_IMAGE_BYTES;
  if (!Number.isFinite(size) || size <= 0 || size > max) {
    throw new Error("O tamanho da mídia não é permitido para Stories.");
  }
  if (delivery.media_kind === "video") {
    const ratio = Number(delivery.width) / Number(delivery.height);
    if (delivery.mime_type !== "video/mp4" || Math.abs(ratio - 9 / 16) > 0.04) {
      throw new Error("O vídeo precisa ser MP4 vertical 9:16.");
    }
    if (!delivery.duration_ms || Number(delivery.duration_ms) > 60_000) {
      throw new Error("O vídeo precisa ter duração verificada de até 60 segundos.");
    }
  } else if (!String(delivery.mime_type).startsWith("image/")) {
    throw new Error("O arquivo configurado não é uma imagem válida.");
  }
  validateStickerStyle(delivery);
}

function validateStickerStyle(delivery) {
  const values = [
    delivery.sticker_x,
    delivery.sticker_y,
    delivery.sticker_width,
    delivery.sticker_height,
    delivery.sticker_rotation,
    delivery.sticker_font_size,
  ].map(Number);
  if (values.some((value) => !Number.isFinite(value))) throw new Error("A edição do adesivo é inválida.");
  const [x, y, width, height, rotation, fontSize] = values;
  if (width < 0.08 || width > 0.9 || height < 0.04 || height > 0.3) throw new Error("O tamanho do adesivo é inválido.");
  if (x < width / 2 || x > 1 - width / 2 || y < height / 2 || y > 1 - height / 2) throw new Error("O adesivo precisa ficar dentro do Story.");
  if (rotation < -180 || rotation > 180 || fontSize < 14 || fontSize > 32) throw new Error("A rotação ou o texto do adesivo é inválido.");
  if (!Object.hasOwn(STORY_FONTS, delivery.sticker_font_family)) throw new Error("A fonte escolhida não é permitida.");
  if (!STORY_COLORS.has(delivery.sticker_text_color) || !STORY_COLORS.has(delivery.sticker_background_color)) {
    throw new Error("As cores escolhidas não pertencem à paleta permitida.");
  }
}

async function normalizeStoryImage(blob, delivery) {
  const bitmap = await createImageBitmap(blob);
  try {
    const width = 1080;
    const height = 1920;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d", { alpha: false });
    context.fillStyle = "#000000";
    context.fillRect(0, 0, width, height);
    const scale = Math.min(width / bitmap.width, height / bitmap.height);
    const drawWidth = Math.round(bitmap.width * scale);
    const drawHeight = Math.round(bitmap.height * scale);
    context.drawImage(
      bitmap,
      Math.round((width - drawWidth) / 2),
      Math.round((height - drawHeight) / 2),
      drawWidth,
      drawHeight,
    );
    drawLinkSticker(context, width, height, delivery);
    return {
      blob: await canvasToBlob(canvas, "image/jpeg", 0.94),
      width,
      height,
      mimeType: "image/jpeg",
    };
  } finally {
    bitmap.close();
  }
}

async function renderStoryVideo(source, delivery) {
  const width = even(Number(delivery.width));
  const height = even(Number(delivery.height));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, width, height);
  drawLinkSticker(context, width, height, delivery);
  const overlay = await canvasToBlob(canvas, "image/png");
  const blob = await compositeVideoOverlay(source, overlay);
  if (blob.size > MAX_VIDEO_BYTES) {
    throw new Error("O vídeo renderizado ultrapassou 100 MB. Reduza a duração ou a resolução.");
  }
  return { blob, width, height, mimeType: "video/mp4" };
}

function drawLinkSticker(context, storyWidth, storyHeight, style) {
  const centerX = Number(style.sticker_x) * storyWidth;
  const centerY = Number(style.sticker_y) * storyHeight;
  const width = Number(style.sticker_width) * storyWidth;
  const height = Number(style.sticker_height) * storyHeight;
  const rotation = Number(style.sticker_rotation) * Math.PI / 180;
  const logicalScale = storyWidth / 360;
  const fontSize = Number(style.sticker_font_size) * logicalScale;
  const family = String(style.sticker_font_family);
  const title = String(style.link_title || safeHost(style.link_url));
  const radius = Math.min(height / 3, 22 * logicalScale);
  const padding = Math.max(8, 10 * logicalScale);
  const iconSize = Math.max(10, fontSize * 0.9);
  const gap = 5 * logicalScale;

  context.save();
  context.translate(centerX, centerY);
  context.rotate(rotation);
  roundedRect(context, -width / 2, -height / 2, width, height, radius);
  context.fillStyle = style.sticker_background_color;
  context.fill();
  context.strokeStyle = "rgba(255, 255, 255, 0.16)";
  context.lineWidth = Math.max(1, height * 0.04);
  context.stroke();
  context.font = `${style.sticker_italic ? "italic " : ""}600 ${fontSize}px "${family}", sans-serif`;
  context.textBaseline = "middle";
  context.textAlign = "left";
  context.fillStyle = style.sticker_text_color;
  const maxTextWidth = Math.max(1, width - padding * 2 - iconSize - gap);
  const fitted = ellipsize(context, title, maxTextWidth);
  const totalWidth = iconSize + gap + context.measureText(fitted).width;
  const startX = -totalWidth / 2;
  drawLinkIcon(context, startX + iconSize / 2, 0, iconSize, style.sticker_text_color);
  context.fillText(fitted, startX + iconSize + gap, fontSize * 0.035, maxTextWidth);
  context.restore();
}

function drawLinkIcon(context, x, y, size, color) {
  context.save();
  context.translate(x, y);
  context.rotate(-Math.PI / 4);
  context.strokeStyle = color;
  context.lineWidth = Math.max(1.5, size * 0.11);
  context.lineCap = "round";
  const radius = size * 0.22;
  context.beginPath();
  context.roundRect(-size * 0.42, -radius, size * 0.52, radius * 2, radius);
  context.stroke();
  context.beginPath();
  context.roundRect(-size * 0.1, -radius, size * 0.52, radius * 2, radius);
  context.stroke();
  context.restore();
}

function roundedRect(context, x, y, width, height, radius) {
  context.beginPath();
  context.roundRect(x, y, width, height, radius);
  context.closePath();
}

function ellipsize(context, text, maxWidth) {
  if (context.measureText(text).width <= maxWidth) return text;
  let value = text;
  while (value.length > 1 && context.measureText(`${value}…`).width > maxWidth) value = value.slice(0, -1);
  return `${value}…`;
}

async function ensureStoryFont(family, italic) {
  if (!document?.fonts || !globalThis.FontFace) return;
  const files = STORY_FONTS[family];
  const style = italic && files[1] ? "italic" : "normal";
  const file = style === "italic" ? files[1] : files[0];
  const key = `${family}:${style}`;
  if (!loadedFonts.has(key)) {
    loadedFonts.set(key, (async () => {
      const face = new FontFace(family, `url(${chrome.runtime.getURL(`fonts/${file}`)})`, { style });
      document.fonts.add(await face.load());
      await document.fonts.ready;
    })());
  }
  await loadedFonts.get(key);
}

function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => canvas.toBlob(
    (blob) => blob ? resolve(blob) : reject(new Error("A renderização do adesivo falhou.")),
    type,
    quality,
  ));
}

function even(value) {
  const rounded = Math.max(2, Math.round(value));
  return rounded % 2 === 0 ? rounded : rounded - 1;
}

async function uploadStoryPhoto(entityName, uploadId, prepared, appId) {
  const params = {
    upload_id: uploadId,
    media_type: 1,
    upload_media_width: prepared.width,
    upload_media_height: prepared.height,
  };
  await uploadStoryEntity(entityName, prepared.blob, params, prepared.mimeType, appId);
}

async function uploadStoryVideo(entityName, uploadId, prepared, appId) {
  const params = {
    "client-passthrough": "1",
    is_sidecar: "0",
    media_type: 2,
    upload_id: uploadId,
    for_album: true,
    is_unified_video: "0",
  };
  await uploadStoryEntity(entityName, prepared.blob, params, prepared.mimeType, appId, true);
}

async function uploadStoryEntity(entityName, blob, params, mimeType, appId, video = false) {
  const endpoint = video ? "rupload_igvideo" : "rupload_igphoto";
  const response = await fetch(`https://i.instagram.com/${endpoint}/${entityName}`, {
    method: "POST",
    credentials: "include",
    body: blob,
    headers: {
      Accept: "*/*",
      "Content-Type": mimeType,
      Offset: "0",
      "X-Entity-Length": String(blob.size),
      "X-Entity-Name": entityName,
      "X-Entity-Type": mimeType,
      "X-IG-App-ID": appId || INSTAGRAM_APP_ID,
      "X-Instagram-Rupload-Params": JSON.stringify(params),
    },
  });
  if (!response.ok) throw new Error(`O Instagram recusou o upload do Story (${response.status}).`);
}

async function configureStory(uploadId, delivery, context) {
  const sticker = {
    x: delivery.sticker_x,
    y: delivery.sticker_y,
    width: delivery.sticker_width,
    height: delivery.sticker_height,
    rotation: delivery.sticker_rotation,
    display_url: safeHost(delivery.link_url),
    link_title: delivery.link_title || safeHost(delivery.link_url),
    link_type: "web",
    link_type_v2: "external",
    url: delivery.link_url,
  };
  const body = new URLSearchParams({
    upload_id: uploadId,
    reel_mentions: "[]",
    story_link_stickers: JSON.stringify([sticker]),
    story_cta: JSON.stringify([{ links: [{ webUri: delivery.link_url }] }]),
  });
  const requestHeaders = {
    Accept: "*/*",
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Csrftoken": context.csrfToken,
    "X-IG-App-ID": context.appId || INSTAGRAM_APP_ID,
  };
  let lastError = "";
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const response = await fetch("https://www.instagram.com/api/v1/web/create/configure_to_story/", {
      method: "POST",
      credentials: "include",
      body: body.toString(),
      headers: requestHeaders,
    });
    const text = await response.text();
    if (response.status === 200) return text;
    lastError = text;
    if (attempt < 4 && (response.status === 202 || text.includes("Transcode not finished"))) {
      await new Promise((resolve) => setTimeout(resolve, Math.min(5_000 * 2 ** attempt, 60_000)));
      continue;
    }
    break;
  }
  const parsed = parseInstagramJson(lastError);
  throw new Error(parsed.message || "O Instagram não concluiu a publicação do Story.");
}

function safeHost(value) {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch {
    return "Link";
  }
}

function parseInstagramJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}
