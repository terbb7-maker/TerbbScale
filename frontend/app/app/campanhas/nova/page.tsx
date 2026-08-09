"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Clock3, LoaderCircle, Send, Shuffle } from "lucide-react";
import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { toast } from "sonner";

import { CampaignCoverPicker } from "@/components/campaign-cover-picker";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";
import type { Account, Campaign, Media, Proxy } from "@/lib/types";

type CampaignPayload = {
  name: string;
  description: string | null;
  caption: string | null;
  hashtags: string[];
  publication_type: string;
  media_strategy: string;
  account_ids: string[];
  media_ids: string[];
  posts_per_hour: number;
  duration_hours: number;
  schedule_distribution: "even" | "burst" | "cooldown";
  post_cooldown_minutes: number;
  schedule_mode: string;
  starts_at: string | null;
  timezone: string;
  cover_mode: "automatic" | "custom";
  custom_cover_media_id: string | null;
  allow_media_reuse: boolean;
  proxy_mode: "none" | "fixed" | "rotate_per_post" | "rotate_every_n_posts";
  proxy_id: string | null;
  proxy_ids: string[];
  proxy_rotation_every: number;
  planning_seed?: string | null;
};
type Preview = {
  valid: boolean;
  errors: string[];
  warnings: string[];
  requested_jobs: number;
  planned_jobs: number;
  planning_seed: string | null;
  items: Array<{
    position: number;
    account_id: string;
    account_username: string;
    media_id: string;
    media_name: string;
    scheduled_at: string;
  }>;
};

export default function NewCampaignPage() {
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api<Account[]>("/accounts?status=connected") });
  const media = useQuery({ queryKey: ["media-ready"], queryFn: () => api<Media[]>("/media?status=ready&limit=200") });
  const proxies = useQuery({ queryKey: ["proxies"], queryFn: () => api<Proxy[]>("/proxies") });
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [selectedMedia, setSelectedMedia] = useState<string[]>([]);
  const [publicationType, setPublicationType] = useState("reel");
  const [coverMode, setCoverMode] = useState<"automatic" | "custom">("automatic");
  const [coverMediaId, setCoverMediaId] = useState<string | null>(null);
  const [coverReady, setCoverReady] = useState(true);
  const [coverProcessing, setCoverProcessing] = useState(false);
  const [scheduleMode, setScheduleMode] = useState("now");
  const [distribution, setDistribution] = useState<"even" | "burst" | "cooldown">("even");
  const [cooldown, setCooldown] = useState("10");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);
  const [proxyMode, setProxyMode] = useState<"none" | "fixed" | "rotate_per_post" | "rotate_every_n_posts">("none");
  const [proxyId, setProxyId] = useState<string | null>(null);
  const [proxyIds, setProxyIds] = useState<string[]>([]);
  const [proxyEvery, setProxyEvery] = useState("1");
  const [proxyDialog, setProxyDialog] = useState(false);

  function payload(form: HTMLFormElement): CampaignPayload {
    const data = new FormData(form);
    const startsAt = String(data.get("starts_at") ?? "");
    return {
      name: String(data.get("name")),
      description: String(data.get("description") || "") || null,
      caption: String(data.get("caption") || "") || null,
      hashtags: String(data.get("hashtags") || "").split(/[\s,]+/).map((tag) => tag.replace(/^#/, "")).filter(Boolean),
      publication_type: publicationType,
      media_strategy: String(data.get("media_strategy")),
      account_ids: selectedAccounts,
      media_ids: selectedMedia,
      posts_per_hour: Number(data.get("posts_per_hour")),
      duration_hours: Number(data.get("duration_hours")),
      schedule_distribution: distribution,
      post_cooldown_minutes: distribution === "cooldown" ? Number(cooldown) : 1,
      schedule_mode: scheduleMode,
      starts_at: scheduleMode === "scheduled" && startsAt ? new Date(startsAt).toISOString() : null,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      cover_mode: coverMode,
      custom_cover_media_id: coverMode === "custom" ? coverMediaId : null,
      allow_media_reuse: data.get("allow_media_reuse") === "on",
      proxy_mode: proxyMode,
      proxy_id: proxyMode === "fixed" ? proxyId : null,
      proxy_ids: proxyMode.startsWith("rotate_") ? proxyIds : [],
      proxy_rotation_every: proxyMode === "rotate_every_n_posts" ? Number(proxyEvery) : 1,
    };
  }

  const submit = useMutation({
    mutationFn: async ({ body, activate }: { body: CampaignPayload; activate: boolean }) => {
      let finalBody = body;
      if (activate) {
        const signature = JSON.stringify(body);
        const validatedPlan = preview && previewSignature === signature
          ? preview
          : await api<Preview>("/campaigns/preview", {
              method: "POST",
              body: JSON.stringify(body),
            });
        if (!validatedPlan.valid || !validatedPlan.planning_seed) {
          throw new Error(validatedPlan.errors[0] ?? "O plano da campanha possui bloqueios.");
        }
        finalBody = { ...body, planning_seed: validatedPlan.planning_seed };
      }
      const campaign = await api<Campaign>("/campaigns", {
        method: "POST",
        body: JSON.stringify(finalBody),
      });
      if (activate) {
        await api(`/campaigns/${campaign.id}/activate`, {
          method: "POST",
          body: JSON.stringify(finalBody),
        });
      }
      return campaign;
    },
    onSuccess: (_, variables) => {
      toast.success(variables.activate ? "Campanha ativada." : "Rascunho salvo.");
      location.assign("/app/campanhas");
    },
    onError: (error) => toast.error(error.message),
  });

  async function previewPlan(form: HTMLFormElement) {
    if (coverMode === "custom" && (!coverMediaId || !coverReady)) {
      toast.error("Selecione uma capa pronta antes de validar o plano.");
      return;
    }
    try {
      const body = payload(form);
      const result = await api<Preview>("/campaigns/preview", { method: "POST", body: JSON.stringify(body) });
      setPreview(result);
      setPreviewSignature(JSON.stringify(body));
      if (result.valid) toast.success("Plano validado.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível validar.");
    }
  }

  function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (coverMode === "custom" && (!coverMediaId || !coverReady)) {
      toast.error("Selecione uma capa pronta antes de salvar a campanha.");
      return;
    }
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    submit.mutate({ body: payload(event.currentTarget), activate: submitter?.value === "activate" });
  }

  const allAccounts = useMemo(() => accounts.data ?? [], [accounts.data]);
  const allMedia = useMemo(() => media.data ?? [], [media.data]);
  const selectableMedia = useMemo(
    () => allMedia.filter((item) => publicationType !== "reel" || item.media_kind === "video"),
    [allMedia, publicationType],
  );
  const coverImages = useMemo(
    () => allMedia.filter((item) => item.media_kind === "image"),
    [allMedia],
  );
  const selectedCover = coverImages.find((item) => item.id === coverMediaId);
  const invalidCover = coverMode === "custom" && (!coverMediaId || !coverReady);
  const toggle = (id: string, current: string[], setter: (value: string[]) => void) =>
    setter(current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);

  return (
    <>
      <PageHeader
        eyebrow="Nova operação"
        title="Criar campanha"
        description="Configure a distribuição e valide o plano exato antes de colocá-lo na fila."
        actions={<Link className="button-secondary" href="/app/campanhas"><ArrowLeft size={15} /> Voltar</Link>}
      />
      <form className="grid gap-4 xl:grid-cols-[1fr_360px]" onSubmit={send}>
        <div className="space-y-4">
          <section className="panel p-5 md:p-6">
            <p className="eyebrow">01 · Conteúdo</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label><span className="mb-2 block text-sm text-zinc-400">Nome</span><input className="input" name="name" required maxLength={160} placeholder="Lançamento de agosto" /></label>
              <label><span className="mb-2 block text-sm text-zinc-400">Tipo de publicação</span><select className="input" name="publication_type" value={publicationType} onChange={(event) => {
                const nextType = event.target.value;
                setPublicationType(nextType);
                setSelectedMedia((current) => nextType === "reel" ? current.filter((id) => allMedia.some((item) => item.id === id && item.media_kind === "video")) : current);
                if (nextType !== "reel") {
                  setCoverMode("automatic");
                  setCoverMediaId(null);
                  setCoverReady(true);
                }
              }}><option value="reel">Reel</option><option value="feed">Feed</option><option value="story">Story</option></select></label>
              <label className="md:col-span-2"><span className="mb-2 block text-sm text-zinc-400">Descrição interna</span><input className="input" name="description" maxLength={2000} /></label>
              <label className="md:col-span-2"><span className="mb-2 block text-sm text-zinc-400">Legenda</span><textarea className="input min-h-28 resize-y" name="caption" maxLength={2200} /></label>
              <label className="md:col-span-2"><span className="mb-2 block text-sm text-zinc-400">Hashtags</span><input className="input" name="hashtags" placeholder="#promoção #novidade" /></label>
            </div>
          </section>

          <section className="panel p-5 md:p-6">
            <div className="flex items-center justify-between"><p className="eyebrow">02 · Contas</p><button type="button" className="text-xs text-violet-400" onClick={() => setSelectedAccounts(selectedAccounts.length === allAccounts.length ? [] : allAccounts.map((item) => item.id))}>Selecionar todas</button></div>
            <div className="mt-5 grid gap-2 sm:grid-cols-2">
              {allAccounts.map((account) => (
                <button type="button" className={`flex items-center gap-3 rounded-xl border p-3 text-left ${selectedAccounts.includes(account.id) ? "border-violet-500 bg-violet-500/5" : "hover:border-zinc-700"}`} key={account.id} onClick={() => toggle(account.id, selectedAccounts, setSelectedAccounts)}>
                  <span className={`grid size-5 place-items-center rounded border ${selectedAccounts.includes(account.id) ? "border-violet-500 bg-violet-500" : ""}`}>{selectedAccounts.includes(account.id) && <Check size={13} />}</span>
                  <span><span className="block text-sm font-medium">@{account.username}</span><span className="text-xs text-zinc-600">{account.account_type ?? "Instagram"}</span></span>
                </button>
              ))}
            </div>
            {!allAccounts.length && <p className="mt-5 text-sm text-zinc-600">Conecte uma conta antes de criar a campanha.</p>}
          </section>

          <section className="panel p-5 md:p-6">
            <div className="flex items-center justify-between"><p className="eyebrow">03 · Mídias</p><button type="button" className="text-xs text-violet-400" onClick={() => setSelectedMedia(selectedMedia.length === selectableMedia.length ? [] : selectableMedia.map((item) => item.id))}>Selecionar todas</button></div>
            <div className="mt-5 grid gap-2 sm:grid-cols-2">
              {selectableMedia.map((item) => (
                <button type="button" className={`flex items-center gap-3 rounded-xl border p-3 text-left ${selectedMedia.includes(item.id) ? "border-violet-500 bg-violet-500/5" : "hover:border-zinc-700"}`} key={item.id} onClick={() => toggle(item.id, selectedMedia, setSelectedMedia)}>
                  <span className={`grid size-5 place-items-center rounded border ${selectedMedia.includes(item.id) ? "border-violet-500 bg-violet-500" : ""}`}>{selectedMedia.includes(item.id) && <Check size={13} />}</span>
                  <span className="min-w-0"><span className="block truncate text-sm font-medium">{item.display_name}</span><span className="text-xs capitalize text-zinc-600">{item.media_kind}</span></span>
                </button>
              ))}
            </div>
            {!selectableMedia.length && <p className="mt-5 text-sm text-zinc-600">{publicationType === "reel" ? "Envie um vídeo à biblioteca para publicar um Reel." : "Envie uma mídia à biblioteca para continuar."}</p>}
          </section>

          {publicationType === "reel" && (
            <CampaignCoverPicker
              images={coverImages}
              mode={coverMode}
              onLibraryRefresh={() => media.refetch()}
              onModeChange={(mode) => {
                setCoverMode(mode);
                if (mode === "automatic") {
                  setCoverMediaId(null);
                  setCoverReady(true);
                } else {
                  setCoverReady(Boolean(coverMediaId));
                }
              }}
              onProcessingChange={setCoverProcessing}
              onSelectionChange={(id, ready) => {
                setCoverMediaId(id);
                setCoverReady(ready);
              }}
              selectedId={coverMediaId}
            />
          )}

          <section className="panel p-5 md:p-6">
            <p className="eyebrow">{publicationType === "reel" ? "05" : "04"} · Configuração de proxy</p>
            <div className="mt-4 flex items-center justify-between rounded-xl border border-zinc-800 p-4"><div><strong className="text-sm">{proxyMode === "none" ? "Conexão direta" : proxyMode === "fixed" ? "Proxy fixa para a campanha" : proxyMode === "rotate_per_post" ? "Troca a cada post" : `Troca a cada ${proxyEvery} posts`}</strong><p className="mt-1 text-xs text-zinc-600">A mesma proxy será usada por todas as contas em cada rodada.</p></div><button type="button" className="button-secondary" onClick={() => setProxyDialog(true)}>Configurar proxies</button></div>
            {proxyDialog && <div className="mt-4 rounded-xl border border-violet-500/30 bg-zinc-950 p-4"><div className="grid gap-3 md:grid-cols-2">{[["none","Conexão direta"],["fixed","Uma proxy fixa"],["rotate_per_post","Trocar a cada post"],["rotate_every_n_posts","Trocar a cada X posts"]].map(([value,label]) => <button type="button" key={value} onClick={() => { setProxyMode(value as typeof proxyMode); if (value !== "fixed") setProxyId(null); }} className={`rounded-lg border p-3 text-left text-sm ${proxyMode === value ? "border-violet-500 bg-violet-500/10" : "border-zinc-800"}`}>{label}</button>)}</div>{proxyMode === "fixed" && <select className="input mt-4" value={proxyId ?? ""} onChange={(event) => setProxyId(event.target.value || null)}><option value="">Selecione uma proxy</option>{(proxies.data ?? []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.status}</option>)}</select>}{proxyMode.startsWith("rotate_") && <><div className="mt-4 grid gap-2 sm:grid-cols-2">{(proxies.data ?? []).filter((item) => item.is_active).map((item) => <label key={item.id} className="flex items-center gap-2 rounded-lg border border-zinc-800 p-3 text-sm"><input type="checkbox" checked={proxyIds.includes(item.id)} onChange={() => setProxyIds(proxyIds.includes(item.id) ? proxyIds.filter((id) => id !== item.id) : [...proxyIds, item.id])} />{item.name} · {item.status}</label>)}</div>{proxyMode === "rotate_every_n_posts" && <label className="mt-4 block"><span className="mb-2 block text-sm text-zinc-400">Posts por proxy (rodadas)</span><input className="input" type="number" min="1" max="1000" value={proxyEvery} onChange={(event) => setProxyEvery(event.target.value)} /></label>}</>}<div className="mt-4 flex justify-end"><button type="button" className="button-primary" onClick={() => setProxyDialog(false)}>Concluir configuração</button></div></div>}
          </section>

          <section className="panel p-5 md:p-6">
            <p className="eyebrow">{publicationType === "reel" ? "06" : "05"} · Distribuição</p>
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <label><span className="mb-2 block text-sm text-zinc-400">Estratégia</span><select className="input" name="media_strategy"><option value="same_media">Mesma mídia</option><option value="sequential">Sequencial</option><option value="random_without_replacement">Aleatória sem repetir</option></select></label>
              <label><span className="mb-2 block text-sm text-zinc-400">Posts por hora por conta</span><input className="input" name="posts_per_hour" type="number" min={1} max={1000} defaultValue={5} /></label>
              <label><span className="mb-2 block text-sm text-zinc-400">Quantidade de horas</span><input className="input" name="duration_hours" type="number" min={1} max={168} defaultValue={2} /></label>
              <div className="md:col-span-2"><span className="mb-2 block text-sm text-zinc-400">Distribuição dos posts dentro de cada hora</span><div className="grid gap-2 md:grid-cols-3">{[["even","Distribuir igualmente"],["burst","Publicar em sequência"],["cooldown","Cooldown personalizado"]].map(([value,label]) => <button type="button" key={value} onClick={() => setDistribution(value as typeof distribution)} className={`rounded-lg border p-3 text-left text-sm ${distribution === value ? "border-violet-500 bg-violet-500/10" : "border-zinc-800"}`}>{label}</button>)}</div>{distribution === "cooldown" && <label className="mt-3 block"><span className="mb-2 block text-sm text-zinc-400">Cooldown entre rodadas (minutos)</span><input className="input max-w-64" type="number" min="1" max="60" value={cooldown} onChange={(event) => setCooldown(event.target.value)} /><p className="mt-1 text-xs text-zinc-600">O sistema valida para manter todos os posts dentro da hora configurada.</p></label>}</div>
            </div>
            <label className="mt-4 flex items-center gap-2 text-sm text-zinc-500"><input name="allow_media_reuse" type="checkbox" /> Permitir reutilizar mídias depois que todas forem usadas</label>
          </section>

          <section className="panel p-5 md:p-6">
            <p className="eyebrow">{publicationType === "reel" ? "07" : "06"} · Agendamento</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {[["now", Send, "Publicar agora", "Inicia assim que a campanha for ativada"], ["scheduled", Clock3, "Agendar", "Escolha uma data e horário"]].map(([value, Icon, title, text]) => {
                const OptionIcon = Icon as typeof Send;
                return <button type="button" className={`rounded-xl border p-4 text-left ${scheduleMode === value ? "border-violet-500 bg-violet-500/5" : ""}`} key={String(value)} onClick={() => setScheduleMode(String(value))}><OptionIcon className="text-zinc-500" size={18} /><strong className="mt-3 block text-sm">{String(title)}</strong><span className="mt-1 block text-xs text-zinc-600">{String(text)}</span></button>;
              })}
            </div>
            {scheduleMode === "scheduled" && <label className="mt-4 block"><span className="mb-2 block text-sm text-zinc-400">Data e hora</span><input className="input" name="starts_at" type="datetime-local" required /></label>}
          </section>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-24 xl:self-start">
          <section className="panel p-5">
            <p className="eyebrow">Resumo</p>
            <dl className="mt-5 space-y-3 text-sm">
              <div className="flex justify-between"><dt className="text-zinc-500">Contas</dt><dd>{selectedAccounts.length}</dd></div>
              <div className="flex justify-between"><dt className="text-zinc-500">Mídias</dt><dd>{selectedMedia.length}</dd></div>
              {publicationType === "reel" && <div className="flex justify-between gap-4"><dt className="text-zinc-500">Capa</dt><dd className="truncate text-right">{coverMode === "automatic" ? "Automática" : coverProcessing ? "Processando…" : selectedCover?.display_name ?? "Não selecionada"}</dd></div>}
              <div className="flex justify-between"><dt className="text-zinc-500">Timezone</dt><dd className="max-w-40 truncate">{Intl.DateTimeFormat().resolvedOptions().timeZone}</dd></div>
            </dl>
            {preview && (
              <div className={`mt-5 rounded-xl border p-4 text-sm ${preview.valid ? "border-emerald-500/30 bg-emerald-500/5" : "border-red-500/30 bg-red-500/5"}`}>
                <p className="font-medium">{preview.valid ? `${preview.planned_jobs} publicações planejadas` : "Plano com bloqueios"}</p>
                {[...preview.errors, ...preview.warnings].map((item) => <p className="mt-2 text-xs text-zinc-500" key={item}>• {item}</p>)}
                {preview.valid && preview.items.length > 0 && (
                  <div className="mt-4 max-h-72 space-y-2 overflow-auto border-t border-white/[0.06] pt-3">
                    {preview.items.slice(0, 12).map((item) => (
                      <div className="rounded-lg bg-black/15 px-3 py-2 text-[11px]" key={`${item.account_id}:${item.position}`}>
                        <p className="truncate font-medium text-zinc-300">@{item.account_username} → {item.media_name}</p>
                        <p className="mt-1 text-zinc-600">{new Date(item.scheduled_at).toLocaleString("pt-BR")}</p>
                      </div>
                    ))}
                    {preview.planned_jobs > 12 && <p className="text-center text-[11px] text-zinc-600">Mostrando as primeiras 12 publicações do plano.</p>}
                  </div>
                )}
              </div>
            )}
            <button type="button" className="button-secondary mt-5 w-full" disabled={coverProcessing || invalidCover} onClick={(event) => previewPlan(event.currentTarget.form!)}><Shuffle size={15} /> Validar plano</button>
            <button className="button-primary mt-2 w-full" name="intent" value="activate" disabled={submit.isPending || coverProcessing || invalidCover || !selectedAccounts.length || !selectedMedia.length}>{submit.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <Send size={16} />} Ativar campanha</button>
            <button className="mt-3 w-full text-sm text-zinc-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-50" name="intent" value="draft" disabled={submit.isPending || coverProcessing || invalidCover}>Salvar como rascunho</button>
          </section>
        </aside>
      </form>
    </>
  );
}
