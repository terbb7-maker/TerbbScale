"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  ImageIcon,
  Italic,
  Link2,
  LoaderCircle,
  Move,
  RotateCcw,
  Save,
  Trash2,
} from "lucide-react";
import { FormEvent, PointerEvent as ReactPointerEvent, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type {
  CookieStoryFontFamily,
  CookieStoryPreset,
  CookieStoryStickerStyle,
  Media,
} from "@/lib/types";

const DEFAULT_STYLE: CookieStoryStickerStyle = {
  sticker_x: 0.5,
  sticker_y: 0.81,
  sticker_width: 0.58,
  sticker_height: 0.1,
  sticker_rotation: 0,
  sticker_font_size: 14,
  sticker_font_family: "Inter",
  sticker_italic: false,
  sticker_text_color: "#ffffff",
  sticker_background_color: "rgba(0, 0, 0, 0.6)",
};

const STORY_FONTS: Array<{ value: CookieStoryFontFamily; label: string; css: string }> = [
  { value: "Inter", label: "Inter", css: '"Story Inter", Inter, sans-serif' },
  { value: "Roboto", label: "Roboto", css: '"Story Roboto", Roboto, sans-serif' },
  { value: "Poppins", label: "Poppins", css: '"Story Poppins", Poppins, sans-serif' },
  { value: "Montserrat", label: "Montserrat", css: '"Story Montserrat", Montserrat, sans-serif' },
  { value: "Bebas Neue", label: "Bebas Neue", css: '"Story Bebas Neue", sans-serif' },
  { value: "Playfair Display", label: "Playfair Display", css: '"Story Playfair Display", Georgia, serif' },
  { value: "Merriweather", label: "Merriweather", css: '"Story Merriweather", Georgia, serif' },
  { value: "Pacifico", label: "Pacifico", css: '"Story Pacifico", cursive' },
  { value: "DancingScript", label: "Dancing Script", css: '"Story DancingScript", cursive' },
  { value: "Anton", label: "Anton", css: '"Story Anton", sans-serif' },
  { value: "Lora", label: "Lora", css: '"Story Lora", Georgia, serif' },
  { value: "Great Vibes", label: "Great Vibes", css: '"Story Great Vibes", cursive' },
];

const STORY_COLORS = [
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
];

export function CookieStoryPresetCard() {
  const client = useQueryClient();
  const previewRef = useRef<HTMLDivElement>(null);
  const [previewWidth, setPreviewWidth] = useState(320);
  const [mediaDraft, setMediaDraft] = useState<string | null>(null);
  const [linkDraft, setLinkDraft] = useState<string | null>(null);
  const [titleDraft, setTitleDraft] = useState<string | null>(null);
  const [styleDraft, setStyleDraft] = useState<CookieStoryStickerStyle | null>(null);

  const preset = useQuery({
    queryKey: ["cookie-story-preset"],
    queryFn: () => api<CookieStoryPreset | null>("/cookie-story/preset"),
  });
  const media = useQuery({
    queryKey: ["cookie-story-media"],
    queryFn: () => api<Media[]>("/media?status=ready&limit=200"),
  });

  useEffect(() => {
    const element = previewRef.current;
    if (!element) return;
    const resize = new ResizeObserver(([entry]) => setPreviewWidth(entry.contentRect.width || 320));
    resize.observe(element);
    return () => resize.disconnect();
  }, []);

  const mediaId = mediaDraft ?? preset.data?.media_id ?? "";
  const linkUrl = linkDraft ?? preset.data?.link_url ?? "";
  const linkTitle = titleDraft ?? preset.data?.link_title ?? "";
  const style = styleDraft ?? styleFromPreset(preset.data);
  const selectedPreview = useQuery({
    queryKey: ["cookie-story-selected-preview", mediaId],
    queryFn: () => api<{ url: string }>(`/media/${mediaId}/preview`),
    enabled: Boolean(mediaId),
    staleTime: 4 * 60 * 1000,
  });
  const previewUrl = selectedPreview.data?.url
    ?? (preset.data?.media_id === mediaId ? preset.data.preview_url : null);

  const save = useMutation({
    mutationFn: () => api<CookieStoryPreset>("/cookie-story/preset", {
      method: "PUT",
      body: JSON.stringify({
        media_id: mediaId,
        link_url: linkUrl,
        link_title: linkTitle.trim() || null,
        ...style,
      }),
    }),
    onSuccess: (saved) => {
      client.setQueryData(["cookie-story-preset"], saved);
      setMediaDraft(null);
      setLinkDraft(null);
      setTitleDraft(null);
      setStyleDraft(null);
      toast.success("Story e edição do link salvos.");
    },
    onError: (error) => toast.error(error.message),
  });
  const remove = useMutation({
    mutationFn: () => api<void>("/cookie-story/preset", { method: "DELETE" }),
    onSuccess: () => {
      client.setQueryData(["cookie-story-preset"], null);
      setMediaDraft("");
      setLinkDraft("");
      setTitleDraft("");
      setStyleDraft(null);
      toast.success("Story predefinido removido.");
    },
    onError: (error) => toast.error(error.message),
  });

  function updateStyle(changes: Partial<CookieStoryStickerStyle>) {
    setStyleDraft(clampStyle({ ...style, ...changes }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!mediaId || !linkUrl) {
      toast.error("Escolha a mídia e informe o link.");
      return;
    }
    save.mutate();
  }

  function beginDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest("[data-editor-control]")) return;
    const rect = previewRef.current?.getBoundingClientRect();
    if (!rect) return;
    event.preventDefault();
    const start = { clientX: event.clientX, clientY: event.clientY, x: style.sticker_x, y: style.sticker_y };
    trackPointer(
      (next) => updateStyle({
        sticker_x: start.x + (next.clientX - start.clientX) / rect.width,
        sticker_y: start.y + (next.clientY - start.clientY) / rect.height,
      }),
    );
  }

  function beginResize(event: ReactPointerEvent<HTMLButtonElement>, corner: string) {
    const rect = previewRef.current?.getBoundingClientRect();
    if (!rect) return;
    event.preventDefault();
    event.stopPropagation();
    const start = {
      clientX: event.clientX,
      clientY: event.clientY,
      width: style.sticker_width,
      height: style.sticker_height,
    };
    trackPointer((next) => {
      const directionX = corner.includes("e") ? 1 : -1;
      const directionY = corner.includes("s") ? 1 : -1;
      updateStyle({
        sticker_width: start.width + directionX * 2 * (next.clientX - start.clientX) / rect.width,
        sticker_height: start.height + directionY * 2 * (next.clientY - start.clientY) / rect.height,
      });
    });
  }

  function beginRotate(event: ReactPointerEvent<HTMLButtonElement>) {
    const rect = previewRef.current?.getBoundingClientRect();
    if (!rect) return;
    event.preventDefault();
    event.stopPropagation();
    const centerX = rect.left + style.sticker_x * rect.width;
    const centerY = rect.top + style.sticker_y * rect.height;
    const startAngle = Math.atan2(event.clientY - centerY, event.clientX - centerX);
    const startRotation = style.sticker_rotation;
    trackPointer((next) => {
      const angle = Math.atan2(next.clientY - centerY, next.clientX - centerX);
      updateStyle({ sticker_rotation: startRotation + (angle - startAngle) * 180 / Math.PI });
    });
  }

  const font = STORY_FONTS.find((item) => item.value === style.sticker_font_family) ?? STORY_FONTS[0];
  const stickerText = linkTitle.trim() || safeHost(linkUrl);
  const visualFontSize = Math.max(8, style.sticker_font_size * previewWidth / 360);

  return (
    <section className="panel mb-5 overflow-hidden">
      <div className="flex flex-col gap-3 border-b p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="eyebrow">Story predefinido</p>
          <h2 className="mt-1 font-semibold">Editor completo do adesivo de link</h2>
          <p className="mt-1 text-xs leading-5 text-zinc-600">
            Arraste, redimensione e gire o adesivo na prévia. A aparência será aplicada à imagem ou ao vídeo antes da publicação.
          </p>
        </div>
        {preset.data && (
          <button className="button-secondary shrink-0 text-red-300" disabled={remove.isPending} onClick={() => remove.mutate()} type="button">
            <Trash2 size={15} /> Remover preset
          </button>
        )}
      </div>

      <form className="grid gap-6 p-5 xl:grid-cols-[minmax(260px,320px)_minmax(0,1fr)]" onSubmit={submit}>
        <div className="mx-auto w-full max-w-[320px]">
          <div ref={previewRef} className="relative aspect-[9/16] touch-none overflow-hidden rounded-2xl border bg-zinc-950 shadow-2xl">
            {previewUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img alt="Prévia do Story" className="size-full object-cover" draggable={false} src={previewUrl} />
            ) : (
              <div className="grid size-full place-items-center text-center text-zinc-700">
                <span><ImageIcon className="mx-auto" size={28} /><small className="mt-3 block">Prévia 9:16</small></span>
              </div>
            )}
            <div className="pointer-events-none absolute inset-x-[6%] inset-y-[4%] rounded-xl border border-dashed border-white/10" />
            {!!linkUrl && (
              <div
                className="absolute z-10 flex cursor-move select-none items-center justify-center rounded-lg border border-white/15 px-2 text-center font-semibold shadow-lg outline outline-1 outline-violet-400/70"
                onPointerDown={beginDrag}
                style={{
                  left: `${style.sticker_x * 100}%`,
                  top: `${style.sticker_y * 100}%`,
                  width: `${style.sticker_width * 100}%`,
                  height: `${style.sticker_height * 100}%`,
                  transform: `translate(-50%, -50%) rotate(${style.sticker_rotation}deg)`,
                  transformOrigin: "center",
                  color: style.sticker_text_color,
                  background: style.sticker_background_color,
                  fontFamily: font.css,
                  fontStyle: style.sticker_italic ? "italic" : "normal",
                  fontSize: visualFontSize,
                }}
              >
                <span className="flex min-w-0 items-center justify-center gap-1.5 overflow-hidden whitespace-nowrap">
                  <Link2 className="shrink-0" size={Math.max(10, visualFontSize * 0.9)} />
                  <span className="truncate">{stickerText}</span>
                </span>
                {(["nw", "ne", "sw", "se"] as const).map((corner) => (
                  <button
                    key={corner}
                    aria-label={`Redimensionar ${corner}`}
                    className={`absolute size-3 rounded-full border border-white bg-violet-500 ${handlePosition(corner)}`}
                    data-editor-control
                    onPointerDown={(event) => beginResize(event, corner)}
                    type="button"
                  />
                ))}
                <button
                  aria-label="Girar adesivo"
                  className="absolute -top-9 left-1/2 grid size-6 -translate-x-1/2 place-items-center rounded-full border border-white/20 bg-zinc-950 text-white"
                  data-editor-control
                  onPointerDown={beginRotate}
                  type="button"
                >
                  <RotateCcw size={12} />
                </button>
              </div>
            )}
          </div>
          <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-[11px] text-zinc-600">
            <Move size={12} /> Arraste o centro · cantos alteram o tamanho · alça superior gira
          </p>
        </div>

        <div className="min-w-0">
          <label>
            <span className="mb-2 block text-sm text-zinc-400">Mídia pronta</span>
            <select className="input" required value={mediaId} onChange={(event) => setMediaDraft(event.target.value)}>
              <option value="">Selecione da biblioteca</option>
              {(media.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.display_name} · {item.media_kind === "video" ? "vídeo" : "imagem"}
                </option>
              ))}
            </select>
          </label>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label>
              <span className="mb-2 block text-sm text-zinc-400">Link HTTPS</span>
              <div className="relative">
                <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" size={16} />
                <input className="input pl-9" maxLength={2048} placeholder="https://seusite.com/oferta" required type="url" value={linkUrl} onChange={(event) => setLinkDraft(event.target.value)} />
              </div>
            </label>
            <label>
              <span className="mb-2 block text-sm text-zinc-400">Texto do adesivo</span>
              <input className="input" maxLength={80} placeholder="Saiba mais" value={linkTitle} onChange={(event) => setTitleDraft(event.target.value)} />
            </label>
          </div>

          <div className="mt-5 rounded-xl border bg-white/[0.015] p-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label>
                <span className="mb-2 block text-xs text-zinc-500">Fonte</span>
                <select className="input" value={style.sticker_font_family} onChange={(event) => updateStyle({ sticker_font_family: event.target.value as CookieStoryFontFamily })}>
                  {STORY_FONTS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
              <div>
                <span className="mb-2 block text-xs text-zinc-500">Estilo</span>
                <button
                  className={`button-secondary w-full ${style.sticker_italic ? "border-violet-400/50 bg-violet-500/10 text-violet-200" : ""}`}
                  onClick={() => updateStyle({ sticker_italic: !style.sticker_italic })}
                  type="button"
                >
                  <Italic size={15} /> Itálico
                </button>
              </div>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <RangeControl label="Tamanho do texto" min={14} max={32} step={1} value={style.sticker_font_size} suffix="px" onChange={(value) => updateStyle({ sticker_font_size: value })} />
              <RangeControl label="Largura" min={8} max={90} step={1} value={Math.round(style.sticker_width * 100)} suffix="%" onChange={(value) => updateStyle({ sticker_width: value / 100 })} />
              <RangeControl label="Altura" min={4} max={30} step={1} value={Math.round(style.sticker_height * 100)} suffix="%" onChange={(value) => updateStyle({ sticker_height: value / 100 })} />
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <RangeControl label="Posição horizontal" min={0} max={100} step={1} value={Math.round(style.sticker_x * 100)} suffix="%" onChange={(value) => updateStyle({ sticker_x: value / 100 })} />
              <RangeControl label="Posição vertical" min={0} max={100} step={1} value={Math.round(style.sticker_y * 100)} suffix="%" onChange={(value) => updateStyle({ sticker_y: value / 100 })} />
              <RangeControl label="Rotação" min={-180} max={180} step={1} value={Math.round(style.sticker_rotation)} suffix="°" onChange={(value) => updateStyle({ sticker_rotation: value })} />
            </div>

            <div className="mt-5 grid gap-5 md:grid-cols-2">
              <ColorPalette label="Cor do texto" selected={style.sticker_text_color} onChange={(value) => updateStyle({ sticker_text_color: value })} />
              <ColorPalette label="Cor do fundo" selected={style.sticker_background_color} onChange={(value) => updateStyle({ sticker_background_color: value })} includeDefault />
            </div>

            <button className="mt-5 text-xs text-zinc-500 underline underline-offset-4 hover:text-zinc-300" onClick={() => setStyleDraft(DEFAULT_STYLE)} type="button">
              Restaurar edição padrão
            </button>
          </div>

          <div className="mt-4 rounded-xl border bg-white/[0.015] p-4 text-xs leading-5 text-zinc-600">
            <p><strong className="text-zinc-400">Imagem:</strong> será enquadrada em 1080×1920 e receberá a edição imediatamente.</p>
            <p><strong className="text-zinc-400">Vídeo:</strong> use MP4 vertical 9:16, até 60 segundos e 100 MB; a extensão renderiza a edição antes do upload.</p>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button className="button-primary" disabled={save.isPending || preset.isLoading || media.isLoading} type="submit">
              {save.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <Save size={16} />} Salvar Story
            </button>
            {preset.data && (
              <span className="inline-flex items-center gap-1.5 text-xs text-emerald-300">
                <Check size={14} /> Preset ativo · {preset.data.media_kind === "video" ? "vídeo" : "imagem"} · {preset.data.media_name}
              </span>
            )}
          </div>
        </div>
      </form>
    </section>
  );
}

function RangeControl({ label, min, max, step, value, suffix, onChange }: {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  suffix: string;
  onChange: (value: number) => void;
}) {
  return (
    <label>
      <span className="mb-2 flex items-center justify-between text-xs text-zinc-500"><span>{label}</span><strong className="text-zinc-300">{value}{suffix}</strong></span>
      <input className="w-full accent-violet-500" max={max} min={min} step={step} type="range" value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function ColorPalette({ label, selected, onChange, includeDefault = false }: {
  label: string;
  selected: string;
  onChange: (value: string) => void;
  includeDefault?: boolean;
}) {
  const colors = includeDefault ? [DEFAULT_STYLE.sticker_background_color, ...STORY_COLORS] : STORY_COLORS;
  return (
    <fieldset>
      <legend className="mb-2 text-xs text-zinc-500">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {colors.map((color, index) => (
          <button
            key={`${color}-${index}`}
            aria-label={`${label}: ${color}`}
            className={`size-7 rounded-md border-2 transition ${sameColor(selected, color) ? "border-violet-400 ring-2 ring-violet-400/20" : "border-white/10"}`}
            onClick={() => onChange(color)}
            style={{ background: color }}
            type="button"
          />
        ))}
      </div>
    </fieldset>
  );
}

function styleFromPreset(preset: CookieStoryPreset | null | undefined): CookieStoryStickerStyle {
  if (!preset) return DEFAULT_STYLE;
  return {
    sticker_x: preset.sticker_x,
    sticker_y: preset.sticker_y,
    sticker_width: preset.sticker_width,
    sticker_height: preset.sticker_height,
    sticker_rotation: preset.sticker_rotation,
    sticker_font_size: preset.sticker_font_size,
    sticker_font_family: preset.sticker_font_family,
    sticker_italic: preset.sticker_italic,
    sticker_text_color: preset.sticker_text_color,
    sticker_background_color: preset.sticker_background_color,
  };
}

function clampStyle(style: CookieStoryStickerStyle): CookieStoryStickerStyle {
  const width = clamp(style.sticker_width, 0.08, 0.9);
  const height = clamp(style.sticker_height, 0.04, 0.3);
  return {
    ...style,
    sticker_width: width,
    sticker_height: height,
    sticker_x: clamp(style.sticker_x, width / 2, 1 - width / 2),
    sticker_y: clamp(style.sticker_y, height / 2, 1 - height / 2),
    sticker_rotation: clamp(style.sticker_rotation, -180, 180),
    sticker_font_size: Math.round(clamp(style.sticker_font_size, 14, 32)),
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, Number.isFinite(value) ? value : min));
}

function sameColor(left: string, right: string) {
  const normalize = (value: string) => value.toLowerCase().replaceAll(" ", "")
    .replace("#ffffff", "rgba(255,255,255,1)")
    .replace("#fff", "rgba(255,255,255,1)");
  return normalize(left) === normalize(right);
}

function trackPointer(onMove: (event: PointerEvent) => void) {
  const move = (event: PointerEvent) => onMove(event);
  const stop = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", stop);
    window.removeEventListener("pointercancel", stop);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", stop, { once: true });
  window.addEventListener("pointercancel", stop, { once: true });
}

function handlePosition(corner: "nw" | "ne" | "sw" | "se") {
  return {
    nw: "-left-1.5 -top-1.5 cursor-nwse-resize",
    ne: "-right-1.5 -top-1.5 cursor-nesw-resize",
    sw: "-bottom-1.5 -left-1.5 cursor-nesw-resize",
    se: "-bottom-1.5 -right-1.5 cursor-nwse-resize",
  }[corner];
}

function safeHost(value: string) {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch {
    return "Link";
  }
}
