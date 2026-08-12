"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Cookie,
  Download,
  ExternalLink,
  FileJson,
  Link2,
  LoaderCircle,
  Send,
  Puzzle,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { CookieStoryPresetCard } from "@/components/cookie-story-preset";
import { api } from "@/lib/api";
import {
  connectorCommand,
  type ConnectorStoryResult,
  type ConnectorStatus,
} from "@/lib/cookie-connector";
import type { CookieStoryDelivery, CookieStoryPreset } from "@/lib/types";

type CookieRecord = {
  domain?: unknown;
  expires?: unknown;
  httpOnly?: unknown;
  name?: unknown;
  path?: unknown;
  sameSite?: unknown;
  secure?: unknown;
  value?: unknown;
};

type CookieBatch = {
  file_name: string;
  cookies: CookieRecord[];
};

const EMPTY_STATUS: ConnectorStatus = { items: [], active_index: 0 };

function currentItem(status: ConnectorStatus) {
  return status.items[status.active_index] ?? null;
}

export default function CookieConnectPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [extensionReady, setExtensionReady] = useState<boolean | null>(null);
  const [status, setStatus] = useState<ConnectorStatus>(EMPTY_STATUS);
  const [readingFiles, setReadingFiles] = useState(false);
  const [sessionActivated, setSessionActivated] = useState(false);
  const [publishingStory, setPublishingStory] = useState(false);

  const storyPreset = useQuery({
    queryKey: ["cookie-story-preset"],
    queryFn: () => api<CookieStoryPreset | null>("/cookie-story/preset"),
  });

  const connect = useMutation({
    mutationFn: () => api<{ authorization_url: string }>("/accounts/connect", { method: "POST" }),
    onSuccess: (data) => {
      sessionStorage.setItem("terbb-account-connect-return", "/app/contas/cookie?connected=1");
      location.assign(data.authorization_url);
    },
    onError: (error) => toast.error(error.message),
  });

  async function refreshStatus() {
    const next = await connectorCommand<ConnectorStatus>("QUEUE_STATUS");
    setStatus(next);
    return next;
  }

  useEffect(() => {
    connectorCommand<{ version: string }>("PING", undefined, 2_000)
      .then(() => {
        setExtensionReady(true);
        return refreshStatus();
      })
      .catch(() => setExtensionReady(false));
  }, []);

  useEffect(() => {
    const connected = new URLSearchParams(location.search).get("connected") === "1";
    if (connected) {
      toast.success("Conta conectada pela API oficial da Meta.");
      history.replaceState(null, "", "/app/contas/cookie");
    }
  }, []);

  async function importFiles(files: FileList | null) {
    if (!files?.length || !extensionReady) return;
    setReadingFiles(true);
    try {
      const batches: CookieBatch[] = [];
      for (const file of Array.from(files)) {
        if (file.size > 256_000) throw new Error(`${file.name}: o arquivo excede 256 KB.`);
        const parsed: unknown = JSON.parse(await file.text());
        const cookies = Array.isArray(parsed)
          ? parsed
          : parsed && typeof parsed === "object" && Array.isArray((parsed as { cookies?: unknown }).cookies)
            ? (parsed as { cookies: CookieRecord[] }).cookies
            : null;
        if (!cookies) throw new Error(`${file.name}: formato de cookies não reconhecido.`);
        batches.push({ file_name: file.name, cookies });
      }
      const next = await connectorCommand<ConnectorStatus>("QUEUE_IMPORT", { batches });
      setStatus(next);
      setSessionActivated(false);
      toast.success(`${next.items.length} arquivo${next.items.length === 1 ? " preparado" : "s preparados"} localmente.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível ler os arquivos.");
    } finally {
      setReadingFiles(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function activateSession() {
    try {
      const next = await connectorCommand<ConnectorStatus>("ACTIVATE_CURRENT");
      setStatus(next);
      setSessionActivated(true);
      toast.success("Sessão aplicada somente neste navegador.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível ativar a sessão.");
    }
  }

  async function publishStory() {
    setPublishingStory(true);
    const toastId = toast.loading("Preparando e publicando o Story…");
    try {
      const delivery = await api<CookieStoryDelivery>("/cookie-story/delivery", { method: "POST" });
      const result = await connectorCommand<ConnectorStoryResult>(
        "PUBLISH_STORY",
        { delivery },
        180_000,
      );
      setStatus(result.status);
      toast.success("Story publicado na conta atual.", { id: toastId });
    } catch (error) {
      await refreshStatus().catch(() => undefined);
      toast.error(error instanceof Error ? error.message : "Não foi possível publicar o Story.", { id: toastId });
    } finally {
      setPublishingStory(false);
    }
  }

  async function openInvites() {
    try {
      await connectorCommand("OPEN_INVITES");
      toast.success("Área de permissões aberta em uma nova aba.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível abrir os convites.");
    }
  }

  async function nextAccount() {
    try {
      const next = await connectorCommand<ConnectorStatus>("NEXT_ACCOUNT");
      setStatus(next);
      setSessionActivated(true);
      toast.success("Próxima sessão ativada.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não existe outra conta na fila.");
    }
  }

  async function clearQueue() {
    try {
      const next = await connectorCommand<ConnectorStatus>("QUEUE_CLEAR");
      setStatus(next);
      setSessionActivated(false);
      toast.success("Fila e dados temporários removidos da extensão.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível limpar a fila.");
    }
  }

  const active = currentItem(status);
  const hasNext = status.active_index + 1 < status.items.length;

  return (
    <>
      <PageHeader
        eyebrow="Conector local"
        title="Conectar com cookie"
        description="Prepare a sessão, publique o Story predefinido localmente e finalize a conexão pelo OAuth oficial da Meta."
        actions={<Link className="button-secondary" href="/app/contas"><ArrowLeft size={16} /> Voltar às contas</Link>}
      />

      <section className="mb-5 rounded-2xl border border-amber-500/20 bg-amber-500/[0.055] p-5">
        <div className="flex gap-3">
          <ShieldCheck className="mt-0.5 shrink-0 text-amber-300" size={19} />
          <div>
            <h2 className="text-sm font-semibold text-amber-100">Dados de sessão sensíveis</h2>
            <p className="mt-1 text-xs leading-5 text-amber-100/60">
              Os arquivos ficam somente na memória temporária da extensão. Eles não são enviados ao backend, ao Supabase ou aos logs. Use apenas sessões de contas que você administra.
            </p>
          </div>
        </div>
      </section>

      <CookieStoryPresetCard />

      {extensionReady === false && (
        <section className="panel mb-5 p-6">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex gap-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-violet-500/10 text-violet-300"><Puzzle size={20} /></span>
              <div>
                <h2 className="font-semibold">Instale o Terbb Cookie Connector</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">Baixe, descompacte e carregue a pasta em <strong className="text-zinc-300">chrome://extensions</strong> usando “Carregar sem compactação”. Depois atualize esta página.</p>
              </div>
            </div>
            <a className="button-primary shrink-0" href="/terbb-cookie-connector.zip" download><Download size={16} /> Baixar extensão</a>
          </div>
        </section>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="panel overflow-hidden">
          <div className="border-b p-5">
            <h2 className="font-semibold">Processo da conta atual</h2>
            <p className="mt-1 text-xs text-zinc-600">Cada ação abre ou altera somente o navegador em uso.</p>
          </div>
          <div className="divide-y">
            <Step number="1" title="Importar cookies" description="Selecione um ou vários exports JSON. Apenas cookies de instagram.com serão usados.">
              <input ref={inputRef} className="hidden" type="file" accept="application/json,.json" multiple onChange={(event) => importFiles(event.target.files)} />
              <button className="button-secondary" disabled={!extensionReady || readingFiles} onClick={() => inputRef.current?.click()}>
                {readingFiles ? <LoaderCircle className="animate-spin" size={16} /> : <FileJson size={16} />} Selecionar JSON
              </button>
            </Step>
            <Step number="2" title="Ativar a sessão" description="Substitui somente os cookies atuais do Instagram e abre a conta em uma nova aba." done={sessionActivated}>
              <button className="button-secondary" disabled={!active} onClick={activateSession}><Cookie size={16} /> Ativar e abrir Instagram</button>
            </Step>
            <Step number="3" title="Postar o Story" description="Publica o Story predefinido com link usando somente a sessão ativa neste navegador." done={active?.story_status === "published"}>
              <button className="button-secondary" disabled={!active || !sessionActivated || !storyPreset.data || publishingStory} onClick={publishStory}>
                {publishingStory ? <LoaderCircle className="animate-spin" size={16} /> : <Send size={16} />} {publishingStory ? "Publicando…" : active?.story_status === "published" ? "Publicar novamente" : "Postar Story"}
              </button>
            </Step>
            <Step number="4" title="Aceitar convite" description="Abre Permissões de apps para você revisar e aceitar o convite pendente da Meta.">
              <button className="button-secondary" disabled={!active || !sessionActivated} onClick={openInvites}><ExternalLink size={16} /> Abrir convites</button>
            </Step>
            <Step number="5" title="Conectar à Meta" description="Inicia o Instagram Login oficial. O Terbb Scale recebe apenas o código OAuth e o token oficial.">
              <button className="button-primary" disabled={!active || !sessionActivated || connect.isPending} onClick={() => connect.mutate()}>
                {connect.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <Link2 size={16} />} Conectar conta
              </button>
            </Step>
            <Step number="6" title="Próxima conta" description="Remove a sessão atual do Instagram, ativa o próximo arquivo da fila e abre a nova conta.">
              <button className="button-secondary" disabled={!hasNext} onClick={nextAccount}><ArrowRight size={16} /> Ir para próxima conta</button>
            </Step>
          </div>
        </section>

        <aside className="panel h-fit overflow-hidden">
          <div className="flex items-center justify-between border-b p-5">
            <div>
              <h2 className="font-semibold">Fila local</h2>
              <p className="mt-1 text-xs text-zinc-600">{status.items.length} conta{status.items.length === 1 ? "" : "s"}</p>
            </div>
            {!!status.items.length && <button className="button-secondary px-3 text-red-300" title="Limpar fila" onClick={clearQueue}><Trash2 size={15} /></button>}
          </div>
          <div className="divide-y">
            {status.items.map((item, index) => (
              <div className={`p-4 ${index === status.active_index ? "bg-violet-500/[0.07]" : ""}`} key={item.id}>
                <div className="flex items-center gap-3">
                  <span className={`grid size-8 shrink-0 place-items-center rounded-lg text-xs font-semibold ${index < status.active_index ? "bg-emerald-500/10 text-emerald-300" : index === status.active_index ? "bg-violet-500/15 text-violet-300" : "bg-white/[0.035] text-zinc-600"}`}>
                    {index < status.active_index ? <CheckCircle2 size={15} /> : index + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{item.file_name}</p>
                    <p className="mt-1 text-[11px] text-zinc-600">Conta {item.account_hint} · {item.cookie_count} cookies válidos</p>
                    {item.story_status === "published" && <p className="mt-1 text-[11px] text-emerald-400">Story publicado</p>}
                    {item.story_status === "failed" && <p className="mt-1 truncate text-[11px] text-red-400" title={item.story_error ?? undefined}>Falha no Story</p>}
                  </div>
                </div>
              </div>
            ))}
            {!status.items.length && <div className="px-5 py-14 text-center text-sm text-zinc-600">Importe os arquivos JSON para montar a fila.</div>}
          </div>
        </aside>
      </div>
    </>
  );
}

function Step({
  number,
  title,
  description,
  done = false,
  children,
}: {
  number: string;
  title: string;
  description: string;
  done?: boolean;
  children: React.ReactNode;
}) {
  return (
    <article className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
      <span className={`grid size-9 shrink-0 place-items-center rounded-xl text-sm font-semibold ${done ? "bg-emerald-500/10 text-emerald-300" : "bg-violet-500/10 text-violet-300"}`}>
        {done ? <CheckCircle2 size={17} /> : number}
      </span>
      <div className="min-w-0 flex-1">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-1 text-xs leading-5 text-zinc-600">{description}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </article>
  );
}
