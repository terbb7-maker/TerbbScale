"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Film, ImageIcon, Search, Trash2, UploadCloud } from "lucide-react";
import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import type { Media } from "@/lib/types";

type UploadTicket = { id: string; bucket: string; storage_key: string };

function bytes(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "unit", unit: "megabyte", maximumFractionDigits: 1 }).format(value / 1_048_576);
}

export default function LibraryPage() {
  const input = useRef<HTMLInputElement>(null);
  const client = useQueryClient();
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [dragging, setDragging] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const queryString = new URLSearchParams({ ...(kind && { kind }), ...(status && { status }), ...(search && { search }) });
  const media = useQuery({
    queryKey: ["media", kind, status, search],
    queryFn: () => api<Media[]>(`/media?${queryString}`),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/media/${id}`, { method: "DELETE" }),
    onSuccess: (_, id) => {
      setSelectedIds((current) => current.filter((item) => item !== id));
      toast.success("Mídia removida.");
      client.invalidateQueries({ queryKey: ["media"] });
    },
    onError: (error) => toast.error(error.message),
  });
  const mediaIds = (media.data ?? []).map((item) => item.id);
  const previews = useQuery({
    queryKey: ["media-previews", mediaIds.join(",")],
    queryFn: () => api<{ previews: Array<{ media_id: string; url: string }> }>("/media/previews", {
      method: "POST",
      body: JSON.stringify({ media_ids: mediaIds }),
    }),
    enabled: mediaIds.length > 0,
    staleTime: 12 * 60 * 1000,
  });
  const previewMap = new Map((previews.data?.previews ?? []).map((item) => [item.media_id, item.url]));
  const bulkRemove = useMutation({
    mutationFn: (ids: string[]) => api<{ removed: number }>("/media/bulk-remove", {
      method: "POST",
      body: JSON.stringify({ media_ids: ids }),
    }),
    onSuccess: (result) => {
      toast.success(`${result.removed} mídia${result.removed === 1 ? " removida" : "s removidas"}.`);
      setSelectedIds([]);
      client.invalidateQueries({ queryKey: ["media"] });
    },
    onError: (error) => toast.error(error.message),
  });

  async function uploadFiles(files: File[]) {
    const allowed = files.filter((file) => file.type.startsWith("image/") || file.type.startsWith("video/"));
    for (const file of allowed) {
      const toastId = toast.loading(`Enviando ${file.name}…`);
      try {
        const ticket = await api<UploadTicket>("/media/uploads", {
          method: "POST",
          body: JSON.stringify({ original_name: file.name, mime_type: file.type, size_bytes: file.size }),
        });
        const { error } = await createClient().storage.from(ticket.bucket).upload(ticket.storage_key, file, {
          contentType: file.type,
          upsert: false,
        });
        if (error) throw error;
        await api(`/media/uploads/${ticket.id}/complete`, {
          method: "POST",
          body: JSON.stringify({ storage_key: ticket.storage_key }),
        });
        toast.success(`${file.name} enviado.`, { id: toastId });
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Falha no upload.", { id: toastId });
      }
    }
    client.invalidateQueries({ queryKey: ["media"] });
  }

  function selected(event: ChangeEvent<HTMLInputElement>) {
    void uploadFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  }

  function dropped(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    void uploadFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <>
      <PageHeader
        eyebrow="Assets"
        title="Biblioteca"
        description="Envie, organize e filtre imagens e vídeos prontos para suas campanhas."
        actions={<button className="button-primary" onClick={() => input.current?.click()}><UploadCloud size={16} /> Upload</button>}
      />
      <input ref={input} className="hidden" type="file" multiple accept="image/*,video/*" onChange={selected} />
      <button
        className={`mb-5 flex w-full flex-col items-center justify-center rounded-2xl border border-dashed py-10 ${
          dragging ? "border-violet-400 bg-violet-500/10" : "border-zinc-800 bg-zinc-900/20 hover:border-zinc-700"
        }`}
        onClick={() => input.current?.click()}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={dropped}
      >
        <UploadCloud className="text-zinc-500" size={25} />
        <span className="mt-3 text-sm font-medium">Arraste arquivos ou clique para selecionar</span>
        <span className="mt-1 text-xs text-zinc-600">Imagens e vídeos · seleção múltipla · até 1 GB</span>
      </button>
      {!!selectedIds.length && (
        <section className="mb-4 flex flex-col gap-3 rounded-2xl border border-violet-400/15 bg-violet-500/[0.06] p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm"><strong>{selectedIds.length}</strong> mídia{selectedIds.length === 1 ? " selecionada" : "s selecionadas"}</p>
          <div className="flex gap-2"><button className="button-secondary" onClick={() => setSelectedIds([])}>Cancelar</button><button className="button-danger" disabled={bulkRemove.isPending} onClick={() => confirm(`Remover ${selectedIds.length} mídia${selectedIds.length === 1 ? "" : "s"} da biblioteca?`) && bulkRemove.mutate(selectedIds)}><Trash2 size={15} /> {bulkRemove.isPending ? "Removendo…" : "Remover selecionadas"}</button></div>
        </section>
      )}
      <section className="panel">
        <div className="flex flex-col gap-3 border-b p-4 md:flex-row">
          <label className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" size={16} />
            <input className="input pl-9" placeholder="Pesquisar mídia…" value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <select className="input md:w-40" value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="">Todos os tipos</option><option value="image">Imagem</option><option value="video">Vídeo</option>
          </select>
          <select className="input md:w-40" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Todos os status</option><option value="ready">Pronto</option><option value="processing">Processando</option><option value="invalid">Inválido</option>
          </select>
        </div>
        {!!media.data?.length && <div className="flex items-center justify-between border-b px-4 py-3"><label className="flex items-center gap-2 text-xs text-zinc-500"><input type="checkbox" checked={selectedIds.length === media.data.length} onChange={() => setSelectedIds(selectedIds.length === media.data.length ? [] : media.data.map((item) => item.id))} /> Selecionar todas desta lista</label><span className="text-[11px] text-zinc-700">{media.data.length} itens</span></div>}
        <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {(media.data ?? []).map((item) => (
            <article className={`group relative overflow-hidden rounded-xl border bg-[#0c0e12] ${selectedIds.includes(item.id) ? "border-violet-500/60 ring-2 ring-violet-500/10" : ""}`} key={item.id}>
              <button aria-label={`Selecionar ${item.display_name}`} className={`absolute left-3 top-3 z-10 grid size-7 place-items-center rounded-lg border backdrop-blur ${selectedIds.includes(item.id) ? "border-violet-400 bg-violet-500 text-white" : "border-white/15 bg-black/40 text-transparent hover:text-white"}`} onClick={() => setSelectedIds(selectedIds.includes(item.id) ? selectedIds.filter((id) => id !== item.id) : [...selectedIds, item.id])}><Check size={14} /></button>
              <div className="relative grid aspect-video place-items-center overflow-hidden bg-zinc-900/70">
                {previewMap.get(item.id) ? <div className="absolute inset-0 bg-cover bg-center transition-transform duration-300 group-hover:scale-[1.03]" style={{ backgroundImage: `url(${previewMap.get(item.id)})` }} /> : item.media_kind === "video" ? <Film className="text-zinc-700" size={30} /> : <ImageIcon className="text-zinc-700" size={30} />}
                {item.media_kind === "video" && <span className="absolute bottom-2 right-2 rounded-md bg-black/65 px-2 py-1 text-[10px] text-white backdrop-blur">VÍDEO</span>}
              </div>
              <div className="p-4">
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-medium">{item.display_name}</h3>
                    <p className="mt-1 text-xs text-zinc-600">{bytes(item.size_bytes)} · {item.width && item.height ? `${item.width}×${item.height}` : "analisando"}</p>
                  </div>
                  <button className="text-zinc-600 hover:text-red-400" title="Remover mídia" onClick={() => confirm(`Remover ${item.display_name}?`) && remove.mutate(item.id)}><Trash2 size={15} /></button>
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <StatusBadge status={item.status} />
                  <span className="text-[11px] text-zinc-700">{new Date(item.created_at).toLocaleDateString("pt-BR")}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
        {!media.isLoading && !media.data?.length && <p className="py-16 text-center text-sm text-zinc-600">Nenhuma mídia encontrada.</p>}
      </section>
    </>
  );
}
