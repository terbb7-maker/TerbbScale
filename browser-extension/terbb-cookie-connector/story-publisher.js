const INSTAGRAM_APP_ID = "936619743392459";
const MAX_IMAGE_BYTES = 25 * 1024 * 1024;
const MAX_VIDEO_BYTES = 100 * 1024 * 1024;

import { requireInstagramContext } from "./instagram-session.js";

export async function publishStoryFromDelivery(delivery, expectedAccountId) {
  validateDelivery(delivery);
  const { cookies, headers } = await requireInstagramContext(expectedAccountId);
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

  const source = new Blob([bytes], { type: delivery.mime_type });
  const prepared = delivery.media_kind === "image"
    ? await normalizeStoryImage(source)
    : {
        blob: source,
        width: delivery.width,
        height: delivery.height,
        mimeType: delivery.mime_type,
      };
  const uploadId = String(Date.now());
  const entityName = `story_${uploadId}`;

  if (delivery.media_kind === "image") {
    await uploadStoryPhoto(entityName, uploadId, prepared, headers);
  } else {
    await uploadStoryVideo(entityName, uploadId, prepared, headers);
  }
  const configured = await configureStory(uploadId, delivery, cookies, headers);
  const media = parseInstagramJson(configured).media;
  const publishedLink = media?.pk
    ? `https://www.instagram.com/stories/${media.user?.username || expectedAccountId}/${media.pk}/`
    : null;
  return { publishedLink, mediaId: media?.pk ? String(media.pk) : null };
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
}

async function normalizeStoryImage(blob) {
  const bitmap = await createImageBitmap(blob);
  try {
    const width = 1080;
    const height = 1920;
    const canvas = new OffscreenCanvas(width, height);
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
    return {
      blob: await canvas.convertToBlob({ type: "image/jpeg", quality: 0.94 }),
      width,
      height,
      mimeType: "image/jpeg",
    };
  } finally {
    bitmap.close();
  }
}

async function uploadStoryPhoto(entityName, uploadId, prepared, headers) {
  const params = {
    upload_id: uploadId,
    media_type: 1,
    upload_media_width: prepared.width,
    upload_media_height: prepared.height,
  };
  await uploadStoryEntity(entityName, prepared.blob, params, prepared.mimeType, headers);
}

async function uploadStoryVideo(entityName, uploadId, prepared, headers) {
  const params = {
    "client-passthrough": "1",
    is_sidecar: "0",
    media_type: 2,
    upload_id: uploadId,
    for_album: true,
    is_unified_video: "0",
  };
  await uploadStoryEntity(entityName, prepared.blob, params, prepared.mimeType, headers, true);
}

async function uploadStoryEntity(entityName, blob, params, mimeType, headers, video = false) {
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
      "X-IG-App-ID": headers["x-ig-app-id"] || INSTAGRAM_APP_ID,
      "X-Instagram-Rupload-Params": JSON.stringify(params),
    },
  });
  if (!response.ok) {
    throw new Error(`O Instagram recusou o upload do Story (${response.status}).`);
  }
}

async function configureStory(uploadId, delivery, cookies, headers) {
  const sticker = {
    x: 0.5,
    y: 0.81,
    width: 0.58,
    height: 0.1,
    rotation: 0,
    display_url: new URL(delivery.link_url).hostname.replace(/^www\./, ""),
    link_title: delivery.link_title || new URL(delivery.link_url).hostname.replace(/^www\./, ""),
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
    "X-Csrftoken": cookies.csrftoken,
    "X-IG-App-ID": headers["x-ig-app-id"] || INSTAGRAM_APP_ID,
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

function parseInstagramJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}
