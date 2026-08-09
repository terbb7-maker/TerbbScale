"use client";

import { Check, ImageIcon, LoaderCircle, Sparkles, UploadCloud, X } from "lucide-react";
import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import type { Media } from "@/lib/types";

type UploadTicket = { id: string; bucket: string; storage_key: string };
type MediaPreview = { url: string; expires_at: string };

type Props = {
  images: Media[];
  mode: "automatic" | "custom";
  selectedId: string | null;
  onModeChange: (mode: "automatic" | "custom") => void;
  onSelectionChange: (id: string | null, ready: boolean) => void;
  onProcessingChange: (processing: boolean) => void;
  onLibraryRefresh: () => Promise<unknown>;
};

async function waitUntilReady(mediaId: string): Promise<Media> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const images = await api<Media[]>("/media?kind=image&limit=200");
    const medium = images.find((item) => item.id === mediaId);
    if (medium?.status === "ready") return medium;
    if (medium?.status === "invalid") {
      throw new Error("A imagem enviada não pôde ser processada.");
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("A capa foi enviada, mas ainda está processando. Aguarde e selecione-a na biblioteca.");
}

export function CampaignCoverPicker({
  images,
  mode,
  selectedId,
  onModeChange,
  onSelectionChange,
  onProcessingChange,
  onLibraryRefresh,
}: Props) {
  const input = useRef<HTMLInputElement>(null);
  const objectUrl = useRef<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    if (mode !== "custom" || !selectedId) {
      if (!objectUrl.current) setPreviewUrl(null);
      return;
    }
    let active = true;
    api<MediaPreview>(`/media/${selectedId}/preview`)
      .then((preview) => {
        if (active) setPreviewUrl(preview.url);
      })
      .catch(() => {
        if (active && !objectUrl.current) setPreviewUrl(null);
      });
    return () => {
      active = false;
    };
  }, [mode, selectedId]);

  useEffect(
    () => () => {
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    },
    [],
  );

  function automatic() {
    onModeChange("automatic");
    onSelectionChange(null, true);
    if (objectUrl.current) {
      URL.revokeObjectURL(objectUrl.current);
      objectUrl.current = null;
    }
    setPreviewUrl(null);
  }

  function selectFromLibrary(id: string) {
    if (objectUrl.current) {
      URL.revokeObjectURL(objectUrl.current);
      objectUrl.current = null;
    }
    onModeChange("custom");
    onSelectionChange(id, true);
  }

  async function upload(file: File) {
    if (!file.type.startsWith("image/")) {
      toast.error("Selecione um arquivo de imagem.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      toast.error("A capa deve ter no máximo 20 MB.");
      return;
    }
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    objectUrl.current = URL.createObjectURL(file);
    setPreviewUrl(objectUrl.current);
    onModeChange("custom");
    onSelectionChange(null, false);
    onProcessingChange(true);
    setUploading(true);
    const toastId = toast.loading("Enviando e processando a capa…");
    try {
      const ticket = await api<UploadTicket>("/media/uploads", {
        method: "POST",
        body: JSON.stringify({
          original_name: file.name,
          mime_type: file.type,
          size_bytes: file.size,
        }),
      });
      const { error } = await createClient().storage
        .from(ticket.bucket)
        .upload(ticket.storage_key, file, { contentType: file.type, upsert: false });
      if (error) throw error;
      const medium = await api<Media>(`/media/uploads/${ticket.id}/complete`, {
        method: "POST",
        body: JSON.stringify({ storage_key: ticket.storage_key }),
      });
      onSelectionChange(medium.id, false);
      const ready = await waitUntilReady(medium.id);
      onSelectionChange(ready.id, true);
      await onLibraryRefresh();
      toast.success("Capa pronta para publicação.", { id: toastId });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao enviar a capa.", {
        id: toastId,
      });
    } finally {
      setUploading(false);
      onProcessingChange(false);
    }
  }

  function selected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void upload(file);
    event.target.value = "";
  }

  function dropped(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) void upload(file);
  }

  return (
    <section className="panel p-5 md:p-6">
      <p className="eyebrow">04 · Capa do Reel</p>
      <p className="mt-2 text-sm text-zinc-500">
        Deixe o Instagram escolher um frame ou envie uma thumbnail personalizada.
      </p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <button
          className={`rounded-xl border p-4 text-left ${mode === "automatic" ? "border-violet-500 bg-violet-500/5" : "hover:border-zinc-700"}`}
          onClick={automatic}
          type="button"
        >
          <Sparkles className="text-violet-400" size={19} />
          <strong className="mt-3 block text-sm">Automática</strong>
          <span className="mt-1 block text-xs text-zinc-600">O Instagram seleciona a capa.</span>
        </button>
        <button
          className={`rounded-xl border p-4 text-left ${mode === "custom" ? "border-violet-500 bg-violet-500/5" : "hover:border-zinc-700"}`}
          onClick={() => onModeChange("custom")}
          type="button"
        >
          <ImageIcon className="text-violet-400" size={19} />
          <strong className="mt-3 block text-sm">Personalizada</strong>
          <span className="mt-1 block text-xs text-zinc-600">Escolha ou envie uma imagem.</span>
        </button>
      </div>

      {mode === "custom" && (
        <div className="mt-5 grid gap-4 lg:grid-cols-[220px_1fr]">
          <div className="relative aspect-[9/16] overflow-hidden rounded-xl border bg-zinc-900">
            {previewUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img alt="Preview da capa" className="size-full object-cover" src={previewUrl} />
            ) : (
              <div className="grid size-full place-items-center text-center text-zinc-700">
                <span><ImageIcon className="mx-auto" size={28} /><small className="mt-3 block">Preview 9:16</small></span>
              </div>
            )}
            {previewUrl && (
              <button
                aria-label="Remover capa"
                className="absolute right-2 top-2 grid size-8 place-items-center rounded-full bg-black/70 text-zinc-300 hover:text-white"
                onClick={() => {
                  onSelectionChange(null, false);
                  setPreviewUrl(null);
                }}
                type="button"
              >
                <X size={15} />
              </button>
            )}
          </div>
          <div className="min-w-0">
            <input
              ref={input}
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={selected}
              type="file"
            />
            <button
              className={`flex w-full flex-col items-center justify-center rounded-xl border border-dashed px-4 py-7 ${
                dragging ? "border-violet-400 bg-violet-500/10" : "border-zinc-800 hover:border-zinc-700"
              }`}
              disabled={uploading}
              onClick={() => input.current?.click()}
              onDragEnter={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={dropped}
              type="button"
            >
              {uploading ? <LoaderCircle className="animate-spin text-violet-400" size={22} /> : <UploadCloud className="text-zinc-500" size={22} />}
              <span className="mt-3 text-sm font-medium">{uploading ? "Processando capa…" : "Enviar nova capa"}</span>
              <span className="mt-1 text-xs text-zinc-600">JPG, PNG ou WebP · até 20 MB</span>
            </button>

            <p className="eyebrow mt-5">Ou escolha da biblioteca</p>
            <div className="mt-3 grid max-h-52 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
              {images.map((image) => (
                <button
                  className={`flex min-w-0 items-center gap-2 rounded-lg border p-2.5 text-left ${
                    selectedId === image.id ? "border-violet-500 bg-violet-500/5" : "hover:border-zinc-700"
                  }`}
                  key={image.id}
                  onClick={() => selectFromLibrary(image.id)}
                  type="button"
                >
                  <span className="grid size-8 shrink-0 place-items-center rounded bg-zinc-800 text-zinc-500">
                    {selectedId === image.id ? <Check className="text-violet-300" size={15} /> : <ImageIcon size={15} />}
                  </span>
                  <span className="truncate text-xs">{image.display_name}</span>
                </button>
              ))}
              {!images.length && <p className="py-4 text-xs text-zinc-600">Nenhuma imagem pronta na biblioteca.</p>}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
