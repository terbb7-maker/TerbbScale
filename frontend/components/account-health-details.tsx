"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, CheckCircle2, Clock3 } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { Account, AccountHealthCheck } from "@/lib/types";

function dateTime(value: string | null) {
  return value ? new Date(value).toLocaleString("pt-BR") : "Ainda não disponível";
}

export function AccountHealthDetails({ account }: { account: Account }) {
  const history = useQuery({
    queryKey: ["account-health", account.id],
    queryFn: () => api<AccountHealthCheck[]>(`/accounts/${account.id}/health-checks?limit=10`),
  });
  const inferred = account.health_confidence === "inferred";

  return (
    <div className="border-t bg-zinc-950/40 px-5 py-5 md:pl-16">
      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-xl border bg-zinc-950 p-4"><p className="text-xs text-zinc-600">Última verificação</p><p className="mt-2 text-sm">{dateTime(account.health_checked_at)}</p></div>
        <div className="rounded-xl border bg-zinc-950 p-4"><p className="text-xs text-zinc-600">Último sucesso</p><p className="mt-2 text-sm">{dateTime(account.health_last_success_at)}</p></div>
        <div className="rounded-xl border bg-zinc-950 p-4"><p className="text-xs text-zinc-600">Falhas consecutivas</p><p className="mt-2 text-sm">{account.health_consecutive_failures}</p></div>
        <div className="rounded-xl border bg-zinc-950 p-4"><p className="text-xs text-zinc-600">Confiança</p><p className="mt-2 text-sm capitalize">{account.health_confidence === "confirmed" ? "Confirmado pela API" : inferred ? "Inferido pelo sistema" : "Aguardando evidência"}</p></div>
      </div>
      <div className={`mt-3 flex gap-3 rounded-xl border p-4 ${inferred ? "border-amber-500/20 bg-amber-500/5" : "bg-zinc-950"}`}>
        {account.health_status === "operational" ? <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-400" size={18} /> : <AlertTriangle className="mt-0.5 shrink-0 text-amber-400" size={18} />}
        <div><p className="text-sm font-medium">{account.health_message ?? "Aguardando a primeira verificação oficial."}</p>{account.health_action_required && <p className="mt-1 text-xs leading-5 text-zinc-500">{account.health_action_required}</p>}{(account.health_error_code || account.health_error_subcode) && <p className="mt-2 text-xs text-zinc-600">Meta: código {account.health_error_code ?? "—"} · subcódigo {account.health_error_subcode ?? "—"}</p>}</div>
      </div>
      <div className="mt-5 flex items-center gap-2"><Activity size={15} className="text-violet-400" /><h4 className="text-sm font-medium">Histórico recente</h4></div>
      <div className="mt-3 divide-y overflow-hidden rounded-xl border">
        {(history.data ?? []).map((check) => <div className="flex flex-col gap-2 px-4 py-3 text-xs sm:flex-row sm:items-center" key={check.id}><StatusBadge status={check.status} /><span className="min-w-0 flex-1 truncate text-zinc-500">{check.details.message ?? "Verificação concluída"}</span><time className="flex items-center gap-1 text-zinc-600"><Clock3 size={12} /> {dateTime(check.checked_at)}</time></div>)}
        {!history.isLoading && !history.data?.length && <p className="px-4 py-8 text-center text-xs text-zinc-600">Nenhuma verificação registrada ainda.</p>}
      </div>
    </div>
  );
}
