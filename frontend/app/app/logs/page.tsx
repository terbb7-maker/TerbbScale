"use client";

import { useQuery } from "@tanstack/react-query";
import { RefreshCw, Search } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";

type Log = {
  id: string;
  event_type: string;
  status: string;
  message: string | null;
  occurred_at: string;
  duration_ms: number | null;
  details: Record<string, unknown>;
};

export default function LogsPage() {
  const [status, setStatus] = useState("");
  const logs = useQuery({
    queryKey: ["logs", status],
    queryFn: () => api<Log[]>(`/logs/publications?limit=200${status ? `&status=${status}` : ""}`),
    refetchInterval: 15_000,
  });
  return (
    <>
      <PageHeader
        eyebrow="Observabilidade"
        title="Logs"
        description="Cada tentativa de publicação, resposta sanitizada e tempo de execução em uma trilha pesquisável."
        actions={<button className="button-secondary" onClick={() => logs.refetch()}><RefreshCw size={15} /> Atualizar</button>}
      />
      <section className="panel overflow-hidden">
        <div className="flex flex-col gap-3 border-b p-4 sm:flex-row">
          <label className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" size={16} /><input className="input pl-9" placeholder="Pesquisar nos logs…" /></label>
          <select className="input sm:w-44" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Todos os status</option><option value="succeeded">Sucesso</option><option value="failed">Falha</option><option value="retry_scheduled">Nova tentativa</option></select>
        </div>
        <div className="divide-y">
          {(logs.data ?? []).map((log) => (
            <details className="group p-5" key={log.id}>
              <summary className="flex cursor-pointer list-none flex-col gap-3 sm:flex-row sm:items-center">
                <span className="min-w-0 flex-1"><span className="block text-sm font-medium">{log.event_type.replaceAll("_", " ")}</span><span className="mt-1 block truncate text-xs text-zinc-600">{log.message ?? "Sem mensagem adicional"}</span></span>
                <span className="text-xs text-zinc-600">{new Date(log.occurred_at).toLocaleString("pt-BR")}</span>
                <span className="text-xs text-zinc-600">{log.duration_ms ? `${log.duration_ms} ms` : "—"}</span>
                <StatusBadge status={log.status} />
              </summary>
              <pre className="mt-4 overflow-x-auto rounded-xl border bg-black/20 p-4 text-xs leading-6 text-zinc-500">{JSON.stringify(log.details, null, 2)}</pre>
            </details>
          ))}
        </div>
        {!logs.isLoading && !logs.data?.length && <p className="py-16 text-center text-sm text-zinc-600">Nenhum log de publicação.</p>}
      </section>
    </>
  );
}
