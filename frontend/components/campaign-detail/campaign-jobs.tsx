import { AlertCircle, CalendarClock, ChevronDown, CircleUserRound, Film, Hash } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { formatDate, formatDuration } from "@/lib/format";
import type { CampaignJob } from "@/lib/types";

function Attempt({ attempt }: { attempt: CampaignJob["attempts"][number] }) {
  return (
    <article className="rounded-xl border bg-black/15 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-zinc-300">Tentativa {attempt.attempt_number}</span>
        {attempt.response_status && (
          <span className="rounded bg-zinc-800 px-2 py-0.5 text-[11px] text-zinc-400">HTTP {attempt.response_status}</span>
        )}
        {attempt.error_class && <StatusBadge status="failed" />}
        {attempt.retryable && <span className="text-[11px] text-amber-400">Retentável</span>}
        <span className="ml-auto text-[11px] text-zinc-600">{formatDuration(attempt.duration_ms)}</span>
      </div>
      {attempt.error_class && <p className="mt-3 text-xs text-red-300">{attempt.error_class}</p>}
      <p className="mt-2 text-[11px] text-zinc-600">
        {formatDate(attempt.started_at)} · operação {attempt.request_operation}
      </p>
      <div className="mt-3">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">Resposta sanitizada</p>
        <pre className="max-h-72 overflow-auto rounded-lg bg-black/30 p-3 text-[11px] leading-5 text-zinc-400">
          {JSON.stringify(attempt.sanitized_response ?? {}, null, 2)}
        </pre>
      </div>
    </article>
  );
}

function Job({ job, maxAttempts }: { job: CampaignJob; maxAttempts: number }) {
  return (
    <details className="group border-b last:border-b-0">
      <summary className="grid cursor-pointer list-none gap-3 p-4 hover:bg-white/[0.015] sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_auto] sm:items-center lg:p-5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <StatusBadge status={job.state} />
            <span className="truncate text-sm font-medium">@{job.account_username}</span>
          </div>
          <div className="mt-2 flex min-w-0 items-center gap-2 text-xs text-zinc-600">
            <Film size={13} />
            <span className="truncate">{job.media_name}</span>
          </div>
        </div>
        <div className="space-y-1 text-xs text-zinc-500">
          <p className="flex items-center gap-2"><CalendarClock size={13} /> {formatDate(job.scheduled_at)}</p>
          <p>{job.attempt_count} de até {maxAttempts} tentativa(s) iniciada(s)</p>
        </div>
        <ChevronDown className="text-zinc-600 transition-transform group-open:rotate-180" size={17} />
      </summary>
      <div className="border-t bg-black/10 p-4 lg:p-5">
        {job.last_error_message && (
          <div className="mb-4 rounded-xl border border-red-400/15 bg-red-400/[0.04] p-4">
            <p className="flex items-center gap-2 text-xs font-semibold text-red-300">
              <AlertCircle size={15} /> {job.last_error_class ?? "Erro de publicação"}
            </p>
            <p className="mt-2 text-sm leading-6 text-red-200/70">{job.last_error_message}</p>
            {job.next_attempt_at && <p className="mt-2 text-xs text-amber-400">Nova tentativa: {formatDate(job.next_attempt_at)}</p>}
          </div>
        )}
        <div className="grid gap-3 text-xs text-zinc-500 sm:grid-cols-2 xl:grid-cols-4">
          <p className="flex items-center gap-2"><CircleUserRound size={14} /> @{job.account_username}</p>
          <p className="flex min-w-0 items-center gap-2"><Film size={14} /><span className="truncate">{job.media_name}</span></p>
          <p className="flex items-center gap-2"><Hash size={14} /> Rodada {job.rotation_slot + 1} · posição {job.plan_position + 1}</p>
          <p className="flex items-center gap-2"><Hash size={14} /> Container: {job.external_container_id ?? "—"}</p>
          <p className="flex items-center gap-2"><Hash size={14} /> Publicação: {job.external_media_id ?? "—"}</p>
        </div>
        <div className="mt-5 space-y-3">
          {job.attempts.map((attempt) => <Attempt attempt={attempt} key={attempt.id} />)}
          {!job.attempts.length && (
            <div className="rounded-xl border border-dashed p-5 text-center text-xs text-zinc-600">
              A publicação ainda não iniciou uma tentativa no worker.
            </div>
          )}
        </div>
      </div>
    </details>
  );
}

export function CampaignJobs({
  jobs,
  truncated,
  maxAttempts,
}: {
  jobs: CampaignJob[];
  truncated: boolean;
  maxAttempts: number;
}) {
  return (
    <section className="panel overflow-hidden">
      <header className="border-b p-5">
        <p className="eyebrow">Fila de publicação</p>
        <h2 className="mt-2 text-lg font-semibold">Jobs e tentativas</h2>
        <p className="mt-1 text-xs text-zinc-600">Abra uma publicação para ver IDs da Meta, erros e respostas sanitizadas.</p>
      </header>
      <div>
        {jobs.map((job) => <Job job={job} key={job.id} maxAttempts={maxAttempts} />)}
        {!jobs.length && <p className="py-14 text-center text-sm text-zinc-600">Nenhum job planejado.</p>}
      </div>
      {truncated && <p className="border-t p-4 text-center text-xs text-amber-400">Exibindo os primeiros jobs desta campanha.</p>}
    </section>
  );
}
