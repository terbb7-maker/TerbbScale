"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Eye, Megaphone, Pause, Play, Plus, XCircle } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { Campaign } from "@/lib/types";

export default function CampaignsPage() {
  const client = useQueryClient();
  const campaigns = useQuery({ queryKey: ["campaigns"], queryFn: () => api<Campaign[]>("/campaigns") });
  const action = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => api<Campaign>(`/campaigns/${id}/${action}`, { method: "POST" }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["campaigns"] });
      toast.success("Campanha atualizada.");
    },
    onError: (error) => toast.error(error.message),
  });
  return (
    <>
      <PageHeader
        eyebrow="Orquestração"
        title="Campanhas"
        description="Planeje distribuições, acompanhe o progresso e duplique operações recorrentes."
        actions={<Link className="button-primary" href="/app/campanhas/nova"><Plus size={16} /> Nova campanha</Link>}
      />
      <section className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b text-xs text-zinc-600">
              <tr><th className="px-5 py-4 font-medium">Campanha</th><th className="px-5 py-4 font-medium">Tipo</th><th className="px-5 py-4 font-medium">Estratégia</th><th className="px-5 py-4 font-medium">Progresso</th><th className="px-5 py-4 font-medium">Início</th><th className="px-5 py-4 font-medium">Status</th><th className="px-5 py-4 font-medium" /></tr>
            </thead>
            <tbody className="divide-y">
              {(campaigns.data ?? []).map((campaign) => {
                const done = campaign.succeeded_count + campaign.failed_count;
                const percent = campaign.planned_count ? Math.round((done / campaign.planned_count) * 100) : 0;
                return (
                  <tr key={campaign.id}>
                    <td className="px-5 py-4"><Link className="group block" href={`/app/campanhas/${campaign.id}`}><p className="font-medium group-hover:text-violet-300">{campaign.name}</p><p className="mt-1 text-xs text-zinc-600">{campaign.posts_per_hour}/h por conta · {campaign.duration_hours}h</p></Link></td>
                    <td className="px-5 py-4 capitalize text-zinc-400">{campaign.publication_type}</td>
                    <td className="px-5 py-4 text-zinc-400">{campaign.media_strategy.replaceAll("_", " ")}</td>
                    <td className="px-5 py-4">
                      <div className="w-28"><div className="h-1.5 overflow-hidden rounded-full bg-zinc-800"><i className="block h-full bg-violet-500" style={{ width: `${percent}%` }} /></div><p className="mt-1.5 text-[11px] text-zinc-600">{done}/{campaign.planned_count}</p></div>
                    </td>
                    <td className="px-5 py-4 text-zinc-400">{campaign.starts_at ? new Date(campaign.starts_at).toLocaleString("pt-BR") : "Rascunho"}</td>
                    <td className="px-5 py-4"><StatusBadge status={campaign.state} /></td>
                    <td className="px-5 py-4">
                      <div className="flex justify-end gap-1">
                        <Link title="Ver detalhes" className="grid size-8 place-items-center rounded-lg text-zinc-500 hover:bg-violet-500/10 hover:text-violet-300" href={`/app/campanhas/${campaign.id}`}><Eye size={15} /></Link>
                        <button title="Duplicar" className="grid size-8 place-items-center rounded-lg text-zinc-500 hover:bg-zinc-800 hover:text-white" onClick={() => action.mutate({ id: campaign.id, action: "duplicate" })}><Copy size={15} /></button>
                        {["scheduled", "running"].includes(campaign.state) && <button title="Pausar" className="grid size-8 place-items-center rounded-lg text-zinc-500 hover:bg-zinc-800 hover:text-white" onClick={() => action.mutate({ id: campaign.id, action: "pause" })}><Pause size={15} /></button>}
                        {campaign.state === "paused" && <button title="Retomar" className="grid size-8 place-items-center rounded-lg text-zinc-500 hover:bg-zinc-800 hover:text-white" onClick={() => action.mutate({ id: campaign.id, action: "resume" })}><Play size={15} /></button>}
                        {!["completed", "cancelled"].includes(campaign.state) && <button title="Cancelar" className="grid size-8 place-items-center rounded-lg text-zinc-500 hover:bg-red-500/10 hover:text-red-400" onClick={() => action.mutate({ id: campaign.id, action: "cancel" })}><XCircle size={15} /></button>}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!campaigns.isLoading && !campaigns.data?.length && (
          <div className="py-20 text-center">
            <Megaphone className="mx-auto text-zinc-700" size={27} />
            <h3 className="mt-4 font-medium">Nenhuma campanha</h3>
            <p className="mt-2 text-sm text-zinc-600">Crie um rascunho e visualize o plano antes de publicar.</p>
          </div>
        )}
      </section>
    </>
  );
}
