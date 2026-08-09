import { Activity, Clock3 } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { formatDate, formatDuration } from "@/lib/format";
import type { CampaignEvent } from "@/lib/types";

export function CampaignEvents({ events, truncated }: { events: CampaignEvent[]; truncated: boolean }) {
  return (
    <section className="panel overflow-hidden">
      <header className="border-b p-5">
        <p className="eyebrow">Linha do tempo</p>
        <h2 className="mt-2 text-lg font-semibold">Tudo que aconteceu</h2>
        <p className="mt-1 text-xs text-zinc-600">Eventos mais recentes primeiro, incluindo novas tentativas e respostas do provedor.</p>
      </header>
      <div className="divide-y">
        {events.map((event) => (
          <details className="group p-5" key={event.id}>
            <summary className="flex cursor-pointer list-none flex-col gap-3 sm:flex-row sm:items-center">
              <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-zinc-800 text-zinc-400">
                <Activity size={15} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{event.event_type.replaceAll("_", " ")}</span>
                <span className="mt-1 block text-xs text-zinc-600">
                  {event.account_username ? `@${event.account_username}` : "Sistema"}
                  {event.media_name ? ` · ${event.media_name}` : ""}
                </span>
              </span>
              <span className="flex items-center gap-1.5 text-xs text-zinc-600"><Clock3 size={13} /> {formatDate(event.occurred_at)}</span>
              <StatusBadge status={event.status} />
            </summary>
            <div className="mt-4 rounded-xl border bg-black/15 p-4">
              <p className="text-sm leading-6 text-zinc-400">{event.message ?? "Sem mensagem adicional."}</p>
              <p className="mt-2 text-xs text-zinc-600">Duração: {formatDuration(event.duration_ms)}</p>
              <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-black/30 p-3 text-[11px] leading-5 text-zinc-400">
                {JSON.stringify(event.details, null, 2)}
              </pre>
            </div>
          </details>
        ))}
        {!events.length && <p className="py-14 text-center text-sm text-zinc-600">Nenhum evento registrado ainda.</p>}
      </div>
      {truncated && <p className="border-t p-4 text-center text-xs text-amber-400">A linha do tempo foi limitada aos eventos mais recentes.</p>}
    </section>
  );
}
