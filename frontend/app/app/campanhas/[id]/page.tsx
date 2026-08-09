"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { CampaignEvents } from "@/components/campaign-detail/campaign-events";
import { CampaignJobs } from "@/components/campaign-detail/campaign-jobs";
import { CampaignResources } from "@/components/campaign-detail/campaign-resources";
import { CampaignSummary } from "@/components/campaign-detail/campaign-summary";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { CampaignDetail } from "@/lib/types";

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const campaign = useQuery({
    queryKey: ["campaign", id],
    queryFn: () => api<CampaignDetail>(`/campaigns/${id}`),
    refetchInterval: 5_000,
  });

  if (campaign.isLoading) {
    return <div className="grid min-h-[55vh] place-items-center"><div className="size-7 animate-spin rounded-full border-2 border-zinc-700 border-t-violet-400" /></div>;
  }
  if (campaign.isError || !campaign.data) {
    return (
      <section className="panel mx-auto max-w-xl p-8 text-center">
        <h1 className="text-xl font-semibold">Não foi possível carregar a campanha</h1>
        <p className="mt-3 text-sm text-zinc-500">{campaign.error?.message ?? "Campanha indisponível."}</p>
        <Link className="button-secondary mt-6" href="/app/campanhas"><ArrowLeft size={15} /> Voltar</Link>
      </section>
    );
  }

  const data = campaign.data;
  const hasErrors = data.failed_count > 0 || (data.queue.counts.dead_letter ?? 0) > 0 || (data.queue.counts.failed_permanent ?? 0) > 0;

  return (
    <>
      <Link className="mb-5 inline-flex items-center gap-2 text-xs text-zinc-500 hover:text-white" href="/app/campanhas">
        <ArrowLeft size={14} /> Voltar para campanhas
      </Link>
      <PageHeader
        eyebrow="Acompanhamento da campanha"
        title={data.name}
        description={`${data.publication_type.toUpperCase()} · ${data.posts_per_hour} publicação(ões)/hora por conta · fuso ${data.timezone}`}
        actions={
          <>
            <StatusBadge status={data.state} />
            <button className="button-secondary" onClick={() => campaign.refetch()}><RefreshCw size={15} /> Atualizar</button>
          </>
        }
      />

      {hasErrors && (
        <div className="mb-4 rounded-xl border border-red-400/20 bg-red-400/[0.05] p-4 text-sm text-red-200/80">
          Esta campanha possui falhas. Abra os jobs abaixo para ver a mensagem, o código HTTP e a resposta sanitizada enviada pela Meta.
        </div>
      )}

      <CampaignSummary campaign={data} />
      <div className="mt-4 grid gap-4 2xl:grid-cols-[minmax(0,1.25fr)_minmax(420px,.75fr)]">
        <CampaignJobs jobs={data.jobs} maxAttempts={data.max_attempts} truncated={data.jobs_truncated} />
        <CampaignEvents events={data.events} truncated={data.events_truncated} />
      </div>
      <div className="mt-4">
        <CampaignResources campaign={data} />
      </div>
    </>
  );
}
