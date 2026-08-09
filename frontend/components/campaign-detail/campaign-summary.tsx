import { AlertTriangle, CheckCircle2, Clock3, ListTodo, LoaderCircle, Server } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { formatDate } from "@/lib/format";
import type { CampaignDetail } from "@/lib/types";

export function CampaignSummary({ campaign }: { campaign: CampaignDetail }) {
  const cards = [
    { label: "Total planejado", value: campaign.queue.total, icon: ListTodo, tone: "text-zinc-300" },
    { label: "Publicados", value: campaign.queue.counts.succeeded ?? 0, icon: CheckCircle2, tone: "text-emerald-400" },
    { label: "Em andamento", value: campaign.queue.active, icon: LoaderCircle, tone: "text-violet-400" },
    {
      label: "Com falha",
      value: (campaign.queue.counts.dead_letter ?? 0) + (campaign.queue.counts.failed_permanent ?? 0),
      icon: AlertTriangle,
      tone: "text-red-400",
    },
  ];

  return (
    <>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ label, value, icon: Icon, tone }) => (
          <article className="panel p-5" key={label}>
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-zinc-500">{label}</p>
              <Icon className={tone} size={17} />
            </div>
            <p className="mt-4 text-3xl font-semibold tracking-tight">{value}</p>
          </article>
        ))}
      </section>

      <section className="panel mt-4 p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center">
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium">Progresso da campanha</p>
                <p className="mt-1 text-xs text-zinc-600">
                  {campaign.queue.finished} de {campaign.queue.total} publicações encerradas
                </p>
              </div>
              <span className="text-2xl font-semibold">{campaign.queue.progress_percent}%</span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet-600 to-violet-400 transition-[width]"
                style={{ width: `${campaign.queue.progress_percent}%` }}
              />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.entries(campaign.queue.counts).map(([state, total]) => (
                <span className="flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs text-zinc-500" key={state}>
                  <StatusBadge status={state} />
                  <strong className="text-zinc-300">{total}</strong>
                </span>
              ))}
            </div>
          </div>
          <div className="grid min-w-[260px] gap-3 border-t pt-5 text-xs lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
            <div className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-2 text-zinc-600"><Clock3 size={14} /> Início</span>
              <span className="text-zinc-300">{formatDate(campaign.starts_at)}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-2 text-zinc-600"><Server size={14} /> Scheduler</span>
              {campaign.scheduler ? <StatusBadge status={campaign.scheduler.status} /> : <span>—</span>}
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-zinc-600">Último ciclo</span>
              <span className="text-zinc-300">{formatDate(campaign.scheduler?.last_success_at)}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-zinc-600">Tentativas por publicação</span>
              <span className="text-zinc-300">até {campaign.max_attempts}</span>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
