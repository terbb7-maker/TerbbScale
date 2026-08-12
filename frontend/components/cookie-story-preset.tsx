"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ImageIcon, Link2, LoaderCircle, Save, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { CookieStoryPreset, Media } from "@/lib/types";

export function CookieStoryPresetCard() {
  const client = useQueryClient();
  const [mediaDraft, setMediaDraft] = useState<string | null>(null);
  const [linkDraft, setLinkDraft] = useState<string | null>(null);
  const [titleDraft, setTitleDraft] = useState<string | null>(null);

  const preset = useQuery({
    queryKey: ["cookie-story-preset"],
    queryFn: () => api<CookieStoryPreset | null>("/cookie-story/preset"),
  });
  const media = useQuery({
    queryKey: ["cookie-story-media"],
    queryFn: () => api<Media[]>("/media?status=ready&limit=200"),
  });

  const mediaId = mediaDraft ?? preset.data?.media_id ?? "";
  const linkUrl = linkDraft ?? preset.data?.link_url ?? "";
  const linkTitle = titleDraft ?? preset.data?.link_title ?? "";
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
      }),
    }),
    onSuccess: (saved) => {
      client.setQueryData(["cookie-story-preset"], saved);
      setMediaDraft(null);
      setLinkDraft(null);
      setTitleDraft(null);
      toast.success("Story predefinido salvo.");
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
      toast.success("Story predefinido removido.");
    },
    onError: (error) => toast.error(error.message),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!mediaId || !linkUrl) {
      toast.error("Escolha a mídia e informe o link.");
      return;
    }
    save.mutate();
  }

  return (
    <section className="panel mb-5 overflow-hidden">
      <div className="flex flex-col gap-3 border-b p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="eyebrow">Story predefinido</p>
          <h2 className="mt-1 font-semibold">Mídia e link para todas as contas da fila</h2>
          <p className="mt-1 text-xs leading-5 text-zinc-600">
            A configuração fica no Terbb Scale; a publicação acontece localmente pela sessão ativa do Instagram.
          </p>
        </div>
        {preset.data && (
          <button className="button-secondary shrink-0 text-red-300" disabled={remove.isPending} onClick={() => remove.mutate()} type="button">
            <Trash2 size={15} /> Remover preset
          </button>
        )}
      </div>

      <form className="grid gap-5 p-5 lg:grid-cols-[180px_minmax(0,1fr)]" onSubmit={submit}>
        <div className="relative aspect-[9/16] overflow-hidden rounded-xl border bg-zinc-900">
          {previewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img alt="Prévia do Story" className="size-full object-cover" src={previewUrl} />
          ) : (
            <div className="grid size-full place-items-center text-center text-zinc-700">
              <span><ImageIcon className="mx-auto" size={28} /><small className="mt-3 block">Prévia 9:16</small></span>
            </div>
          )}
          {!!linkUrl && (
            <div className="absolute bottom-24 left-1/2 max-w-[82%] -translate-x-1/2 rounded-lg bg-white px-3 py-2 text-center text-[10px] font-semibold text-black shadow-lg">
              {linkTitle.trim() || safeHost(linkUrl)}
            </div>
          )}
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

          <div className="mt-4 rounded-xl border bg-white/[0.015] p-4 text-xs leading-5 text-zinc-600">
            <p><strong className="text-zinc-400">Imagem:</strong> será enquadrada em 1080×1920 pela extensão.</p>
            <p><strong className="text-zinc-400">Vídeo:</strong> use MP4 vertical 9:16, até 60 segundos e 100 MB.</p>
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

function safeHost(value: string) {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch {
    return "Link";
  }
}
