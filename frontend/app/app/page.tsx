"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  Bookmark,
  Camera,
  Eye,
  Heart,
  Megaphone,
  MessageCircle,
  Plus,
  RefreshCw,
  Send,
  Share2,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EngagementPeriodFilter, type EngagementPeriod } from "@/components/engagement-period-filter";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";

type Point = { day: string; publications: number; failures: number };
type Upcoming = { job_id: string; campaign_name: string; account_username: string; media_name: string; scheduled_at: string; state: string };

const empty: DashboardSummary = {
  total_accounts: 0, connected_accounts: 0, expired_accounts: 0, active_campaigns: 0,
  completed_campaigns: 0, publications_today: 0, publications_yesterday: 0,
  publications_7d: 0, publications_30d: 0, views: null, likes: null, comments: null,
  shares: null, saves: null, engagement_rate: null, engagement_period: "today",
  engagement_date_from: "", engagement_date_to: "", insights_status: "no_publications",
  insights_updated_at: null, queue_depth: 0, total_proxies: 0, online_proxies: 0,
  offline_proxies: 0, average_proxy_latency_ms: null, accounts_using_proxy: 0,
  campaigns_using_proxy: 0,
};

function formatNumber(value: number | null) {
  if (value === null) return "—";
  return new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function inputDate(daysFromToday = 0) {
  const value = new Date();
  value.setDate(value.getDate() + daysFromToday);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function formatDateRange(from: string, to: string) {
  if (!from || !to) return "Período selecionado";
  const br = (value: string) => value.split("-").reverse().join("/");
  return from === to ? br(from) : `${br(from)} — ${br(to)}`;
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState<EngagementPeriod>("today");
  const [dateFrom, setDateFrom] = useState(() => inputDate(-6));
  const [dateTo, setDateTo] = useState(() => inputDate());
  const validRange = dateFrom <= dateTo;
  const params = new URLSearchParams({ period });
  if (period === "custom") { params.set("date_from", dateFrom); params.set("date_to", dateTo); }

  const summary = useQuery({
    queryKey: ["dashboard", period, dateFrom, dateTo],
    queryFn: () => api<DashboardSummary>(`/dashboard/summary?${params}`),
    enabled: period !== "custom" || validRange,
    placeholderData: (previous) => previous,
  });
  const timeseries = useQuery({ queryKey: ["timeseries"], queryFn: () => api<Point[]>("/dashboard/timeseries?days=30") });
  const upcoming = useQuery({ queryKey: ["upcoming"], queryFn: () => api<Upcoming[]>("/dashboard/upcoming") });
  const data = summary.data ?? empty;

  useEffect(() => {
    let socket: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;
    async function connect() {
      try {
        const { ticket } = await api<{ ticket: string }>("/auth/ws-ticket", { method: "POST" });
        if (cancelled) return;
        const base = new URL(process.env.NEXT_PUBLIC_API_URL ?? "/api/v1", window.location.origin);
        base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
        base.pathname = `${base.pathname.replace(/\/$/, "")}/ws/dashboard`;
        base.search = new URLSearchParams({ ticket }).toString();
        socket = new WebSocket(base);
        socket.onmessage = (message) => {
          const payload = JSON.parse(message.data) as { event?: string };
          if (payload.event && !["connected", "heartbeat"].includes(payload.event)) {
            void Promise.all([
              queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
              queryClient.invalidateQueries({ queryKey: ["timeseries"] }),
              queryClient.invalidateQueries({ queryKey: ["upcoming"] }),
            ]);
          }
        };
        socket.onclose = () => { if (!cancelled) timer = setTimeout(connect, 5000); };
      } catch { if (!cancelled) timer = setTimeout(connect, 10000); }
    }
    void connect();
    return () => { cancelled = true; if (timer) clearTimeout(timer); socket?.close(); };
  }, [queryClient]);

  const metrics = [
    { label: "Publicações hoje", value: data.publications_today, detail: `${data.publications_yesterday} ontem`, icon: Send, color: "text-violet-400", bg: "bg-violet-500/10" },
    { label: "Campanhas ativas", value: data.active_campaigns, detail: `${data.completed_campaigns} finalizadas`, icon: Megaphone, color: "text-fuchsia-400", bg: "bg-fuchsia-500/10" },
    { label: "Contas conectadas", value: data.connected_accounts, detail: `${data.total_accounts} no total`, icon: Camera, color: "text-cyan-400", bg: "bg-cyan-500/10" },
    { label: "Próximos posts", value: data.queue_depth, detail: "na fila de publicação", icon: Activity, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  ];
  const engagement = [
    { label: "Views", value: data.views, icon: Eye },
    { label: "Curtidas", value: data.likes, icon: Heart },
    { label: "Comentários", value: data.comments, icon: MessageCircle },
    { label: "Compartilhamentos", value: data.shares, icon: Share2 },
    { label: "Salvamentos", value: data.saves, icon: Bookmark },
    { label: "Engajamento", value: data.engagement_rate, suffix: "%", icon: TrendingUp },
  ];

  return (
    <>
      <section className="relative mb-5 overflow-hidden rounded-[22px] border border-violet-400/10 bg-[linear-gradient(120deg,#171024,#100c18_55%,#0e0c15)] p-6 sm:p-8">
        <div className="absolute -right-20 -top-24 size-72 rounded-full bg-violet-600/15 blur-3xl" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="eyebrow">Visão geral</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Tudo sob controle.</h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-zinc-500">Veja o que está acontecendo agora e escolha sua próxima ação.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button aria-label="Atualizar dashboard" className="button-secondary px-3" onClick={() => summary.refetch()} disabled={summary.isFetching}><RefreshCw size={16} className={summary.isFetching ? "animate-spin" : ""} /></button>
            <Link className="button-primary" href="/app/campanhas/nova"><Plus size={16} /> Nova campanha</Link>
          </div>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, detail, icon: Icon, color, bg }) => (
          <article className="panel panel-hover p-5" key={label}>
            <div className="flex items-start justify-between"><div><p className="text-xs font-semibold uppercase tracking-[.08em] text-zinc-600">{label}</p><p className="mt-4 text-3xl font-semibold tracking-[-.04em]">{formatNumber(value)}</p></div><span className={`grid size-10 place-items-center rounded-xl ${bg} ${color}`}><Icon size={18} /></span></div>
            <p className="mt-3 text-xs text-zinc-600">{detail}</p>
          </article>
        ))}
      </section>

      <section className="mt-4 grid gap-4 xl:grid-cols-[1.35fr_.65fr]">
        <article className="panel min-h-[370px] p-5 sm:p-6">
          <div className="mb-7 flex items-center justify-between"><div><h2 className="font-semibold">Ritmo de publicação</h2><p className="mt-1 text-xs text-zinc-600">Últimos 30 dias</p></div><span className="rounded-lg bg-violet-500/8 px-2.5 py-1.5 text-xs text-violet-300">30 dias</span></div>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%"><AreaChart data={timeseries.data ?? []}>
              <defs><linearGradient id="publications" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#954cff" stopOpacity={0.42} /><stop offset="100%" stopColor="#954cff" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid stroke="rgba(255,255,255,.055)" vertical={false} /><XAxis dataKey="day" stroke="#625d6d" tickLine={false} axisLine={false} fontSize={11} /><YAxis stroke="#625d6d" tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#15121e", border: "1px solid rgba(255,255,255,.09)", borderRadius: 12 }} /><Area type="monotone" dataKey="publications" stroke="#a365ff" fill="url(#publications)" strokeWidth={2.5} />
            </AreaChart></ResponsiveContainer>
          </div>
        </article>

        <article className="panel p-5 sm:p-6">
          <div className="flex items-start justify-between"><div><h2 className="font-semibold">Engajamento</h2><p className="mt-1 text-xs text-zinc-600">{formatDateRange(data.engagement_date_from, data.engagement_date_to)}</p></div><TrendingUp size={18} className="text-violet-400" /></div>
          <EngagementPeriodFilter dateFrom={dateFrom} dateTo={dateTo} maxDate={inputDate()} onDateFromChange={setDateFrom} onDateToChange={setDateTo} onPeriodChange={setPeriod} period={period} />
          {data.insights_status === "permission_required" && <Link className="mt-4 block rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs leading-5 text-amber-200" href="/app/contas">Reconecte o Instagram para liberar as métricas →</Link>}
          {data.insights_status === "no_publications" && <p className="mt-4 rounded-xl border p-3 text-xs leading-5 text-zinc-500">As métricas aparecem após sua primeira publicação.</p>}
          <div className="mt-4 grid grid-cols-2 gap-2">
            {engagement.map(({ label, value, suffix, icon: Icon }) => <div className="rounded-xl border border-white/[0.055] bg-white/[0.018] p-3" key={label}><div className="flex items-center gap-2 text-[11px] text-zinc-600"><Icon size={13} className="text-violet-400" />{label}</div><strong className="mt-2 block text-lg">{formatNumber(value)}{suffix}</strong></div>)}
          </div>
          {data.insights_updated_at && <p className="mt-3 text-[10px] text-zinc-700">Atualizado em {new Date(data.insights_updated_at).toLocaleString("pt-BR")}</p>}
        </article>
      </section>

      <section className="panel mt-4 overflow-hidden">
        <div className="flex items-center justify-between border-b p-5"><div><h2 className="font-semibold">Próximas publicações</h2><p className="mt-1 text-xs text-zinc-600">O que será publicado a seguir</p></div><Link className="flex items-center gap-1.5 text-xs font-medium text-violet-400 hover:text-violet-300" href="/app/campanhas">Ver campanhas <ArrowRight size={14} /></Link></div>
        <div className="divide-y">
          {(upcoming.data ?? []).slice(0, 5).map((item) => <div className="grid gap-3 px-5 py-4 sm:grid-cols-[1fr_1fr_auto] sm:items-center" key={item.job_id}><div><p className="text-sm font-medium">{item.campaign_name}</p><p className="mt-1 truncate text-xs text-zinc-600">{item.media_name}</p></div><p className="text-xs text-zinc-500">@{item.account_username}</p><div className="flex items-center justify-between gap-4 sm:justify-end"><span className="text-xs text-zinc-500">{new Date(item.scheduled_at).toLocaleString("pt-BR")}</span><StatusBadge status={item.state} /></div></div>)}
          {!upcoming.isLoading && !upcoming.data?.length && <div className="px-6 py-12 text-center"><p className="text-sm text-zinc-500">Sua fila está vazia.</p><Link className="mt-3 inline-flex text-xs font-medium text-violet-400" href="/app/campanhas/nova">Criar primeira campanha →</Link></div>}
        </div>
      </section>
    </>
  );
}
