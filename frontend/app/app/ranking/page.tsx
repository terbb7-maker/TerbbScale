"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bookmark,
  CalendarDays,
  Eye,
  Heart,
  LoaderCircle,
  MessageCircle,
  RefreshCw,
  Send,
  Share2,
  Sparkles,
  TrendingUp,
  Trophy,
} from "lucide-react";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";
import type { MonthlyRanking, MonthlyRankingEntry } from "@/lib/types";

const metricIcons = {
  publications: Send,
  views: Eye,
  likes: Heart,
  comments: MessageCircle,
  shares: Share2,
  saves: Bookmark,
  engagement_rate: TrendingUp,
};

const podiumStyle: Record<number, string> = {
  1: "border-amber-300/25 bg-[linear-gradient(145deg,rgba(245,185,66,.13),rgba(20,18,30,.98))] shadow-[0_24px_80px_rgba(245,185,66,.08)]",
  2: "border-zinc-300/15 bg-[linear-gradient(145deg,rgba(212,212,216,.08),rgba(20,18,30,.98))]",
  3: "border-orange-400/15 bg-[linear-gradient(145deg,rgba(194,105,55,.09),rgba(20,18,30,.98))]",
};

function currentMonth() {
  const parts = new Intl.DateTimeFormat("en", {
    month: "2-digit",
    timeZone: "America/Sao_Paulo",
    year: "numeric",
  }).formatToParts(new Date());
  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  return `${year}-${month}`;
}

function compact(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function exact(value: number) {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(value);
}

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "TS";
}

function dateRange(from: string, to: string) {
  const format = (value: string) => value.split("-").reverse().join("/");
  return `${format(from)} — ${format(to)}`;
}

function Metrics({ entry, compactMode = false }: { entry: MonthlyRankingEntry; compactMode?: boolean }) {
  const metrics = [
    ["publications", "Posts", entry.publications, ""],
    ["views", "Views", entry.views, ""],
    ["likes", "Curtidas", entry.likes, ""],
    ["comments", "Comentários", entry.comments, ""],
    ["shares", "Compart.", entry.shares, ""],
    ["saves", "Salvos", entry.saves, ""],
    ["engagement_rate", "Engajamento", entry.engagement_rate, "%"],
  ] as const;
  return (
    <div className={`grid gap-2 ${compactMode ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-2 sm:grid-cols-4 xl:grid-cols-7"}`}>
      {metrics.map(([key, label, value, suffix]) => {
        const Icon = metricIcons[key];
        return (
          <div className="rounded-xl border border-white/[0.055] bg-black/10 px-3 py-2.5" key={key}>
            <span className="flex items-center gap-1.5 text-[10px] text-zinc-600"><Icon size={11} className="text-violet-400" />{label}</span>
            <strong className="mt-1.5 block text-sm font-semibold text-zinc-200">{compact(value)}{suffix}</strong>
          </div>
        );
      })}
    </div>
  );
}

export default function RankingPage() {
  const [month, setMonth] = useState(currentMonth);
  const ranking = useQuery({
    queryKey: ["monthly-ranking", month],
    queryFn: () => api<MonthlyRanking>(`/ranking/monthly?month=${month}`),
    refetchInterval: 60_000,
  });
  const data = ranking.data;
  const podium = useMemo(() => data?.entries.filter((entry) => entry.position <= 3) ?? [], [data]);
  const ownEntry = data?.entries.find((entry) => entry.is_current_user);

  return (
    <>
      <PageHeader
        eyebrow="Comunidade Terbb"
        title="Ranking mensal"
        description="O desempenho geral de cada usuário em um único placar. Views têm o maior peso natural, e todas as métricas ficam visíveis."
        actions={(
          <div className="flex items-center gap-2">
            <label className="relative">
              <CalendarDays className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-violet-400" size={15} />
              <input aria-label="Mês do ranking" className="input min-h-[42px] w-[170px] pl-9" max={currentMonth()} onChange={(event) => setMonth(event.target.value)} type="month" value={month} />
            </label>
            <button aria-label="Atualizar ranking" className="button-secondary px-3" disabled={ranking.isFetching} onClick={() => ranking.refetch()}><RefreshCw className={ranking.isFetching ? "animate-spin" : ""} size={16} /></button>
          </div>
        )}
      />

      {ranking.isLoading && <div className="panel grid min-h-[420px] place-items-center"><div className="text-center"><LoaderCircle className="mx-auto animate-spin text-violet-400" size={28} /><p className="mt-3 text-sm text-zinc-500">Calculando o ranking...</p></div></div>}
      {ranking.isError && <div className="panel p-8 text-center"><p className="text-sm text-rose-300">Não foi possível carregar o ranking.</p><button className="button-secondary mt-4" onClick={() => ranking.refetch()}>Tentar novamente</button></div>}

      {data && (
        <>
          <section className="relative mb-4 overflow-hidden rounded-[22px] border border-violet-400/10 bg-[linear-gradient(120deg,#171024,#100c18_55%,#0e0c15)] p-5 sm:p-6">
            <div className="absolute -right-16 -top-28 size-64 rounded-full bg-violet-600/15 blur-3xl" />
            <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div><p className="eyebrow">Período oficial</p><h2 className="mt-2 text-xl font-semibold">{dateRange(data.period_start, data.period_end)}</h2><p className="mt-1 text-xs text-zinc-600">{data.is_current_month ? "Ranking em andamento" : "Ranking encerrado"} · Horário de Brasília</p></div>
              <div className="flex gap-2"><div className="rounded-xl border border-white/[0.06] bg-black/15 px-4 py-3 text-right"><p className="text-[10px] uppercase tracking-wider text-zinc-600">Participantes</p><strong className="mt-1 block text-xl">{data.total_participants}</strong></div>{ownEntry && <div className="rounded-xl border border-violet-400/15 bg-violet-500/8 px-4 py-3 text-right"><p className="text-[10px] uppercase tracking-wider text-violet-400">Sua posição</p><strong className="mt-1 block text-xl text-violet-200">#{ownEntry.position}</strong></div>}</div>
            </div>
          </section>

          {podium.length > 0 && (
            <section className="mb-4 grid gap-3 lg:grid-cols-3">
              {podium.map((entry) => (
                <article className={`relative overflow-hidden rounded-[20px] border p-5 ${podiumStyle[entry.position]}`} key={entry.user_id}>
                  <div className="flex items-start justify-between"><div className="flex items-center gap-3"><span className="grid size-11 place-items-center rounded-2xl bg-violet-500/12 text-sm font-bold text-violet-200">{initials(entry.full_name)}</span><div><div className="flex items-center gap-2"><h2 className="font-semibold">{entry.full_name}</h2>{entry.is_current_user && <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-violet-300">Você</span>}</div><p className="mt-1 text-xs text-zinc-600">Score {exact(entry.score)}</p></div></div><span className="grid size-9 place-items-center rounded-xl bg-black/15 font-bold text-violet-200">#{entry.position}</span></div>
                  <div className="mt-5 flex items-end justify-between"><div><p className="text-[10px] uppercase tracking-wider text-zinc-600">Pontuação total</p><strong className="mt-1 block text-3xl tracking-[-.04em]">{compact(entry.score)}</strong></div><Trophy className={entry.position === 1 ? "text-amber-300" : "text-zinc-500"} size={26} /></div>
                  <div className="mt-4"><Metrics compactMode entry={entry} /></div>
                </article>
              ))}
            </section>
          )}

          <section className="panel overflow-hidden">
            <div className="flex items-center justify-between border-b px-5 py-4"><div><h2 className="font-semibold">Classificação geral</h2><p className="mt-1 text-xs text-zinc-600">Score bruto com detalhamento completo</p></div><Sparkles className="text-violet-400" size={17} /></div>
            <div className="divide-y">
              {data.entries.map((entry) => (
                <article className={`p-4 sm:p-5 ${entry.is_current_user ? "bg-violet-500/[0.055]" : ""}`} key={entry.user_id}>
                  <div className="mb-4 flex items-center gap-3"><span className={`grid size-9 shrink-0 place-items-center rounded-xl text-sm font-bold ${entry.position <= 3 ? "bg-violet-500/15 text-violet-200" : "bg-white/[0.035] text-zinc-500"}`}>#{entry.position}</span><span className="grid size-10 shrink-0 place-items-center rounded-xl border border-violet-400/10 bg-violet-500/8 text-xs font-bold text-violet-300">{initials(entry.full_name)}</span><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><h3 className="truncate text-sm font-semibold">{entry.full_name}</h3>{entry.is_current_user && <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-violet-300">Você</span>}</div><p className="mt-1 text-xs text-zinc-600">Score geral: <span className="font-semibold text-zinc-300">{exact(entry.score)}</span></p></div></div>
                  <Metrics entry={entry} />
                </article>
              ))}
              {data.entries.length === 0 && <div className="px-6 py-16 text-center"><Trophy className="mx-auto text-zinc-700" size={30} /><h2 className="mt-4 font-semibold">O ranking ainda está vazio</h2><p className="mt-2 text-sm text-zinc-600">As posições aparecem após as primeiras publicações concluídas do mês.</p></div>}
            </div>
          </section>

          <p className="mt-4 text-center text-[11px] leading-5 text-zinc-700">Score = posts + views + curtidas + comentários + compartilhamentos + salvamentos + taxa de engajamento. Métricas atualizadas dos posts publicados no mês.</p>
        </>
      )}
    </>
  );
}
