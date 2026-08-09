import { CircleUserRound, Film, ImageIcon } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { formatBytes, formatDate, formatDuration } from "@/lib/format";
import type { CampaignDetail } from "@/lib/types";

export function CampaignResources({ campaign }: { campaign: CampaignDetail }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <section className="panel overflow-hidden">
        <header className="border-b p-5">
          <p className="eyebrow">Destino</p>
          <h2 className="mt-2 text-lg font-semibold">Contas selecionadas</h2>
        </header>
        <div className="divide-y">
          {campaign.accounts.map((account) => (
            <article className="flex items-center gap-3 p-4" key={account.id}>
              {account.profile_picture_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img alt="" className="size-10 rounded-full object-cover" src={account.profile_picture_url} />
              ) : (
                <span className="grid size-10 place-items-center rounded-full bg-zinc-800 text-zinc-500"><CircleUserRound size={18} /></span>
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">@{account.username}</p>
                <p className="mt-1 text-xs text-zinc-600">
                  {Object.entries(account.job_counts).map(([state, count]) => `${state}: ${count}`).join(" · ") || "Sem jobs"}
                </p>
              </div>
              <div className="text-right">
                <StatusBadge status={account.status} />
                <p className="mt-2 text-[10px] text-zinc-600">Token: {formatDate(account.token_expires_at)}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel overflow-hidden">
        <header className="border-b p-5">
          <p className="eyebrow">Conteúdo</p>
          <h2 className="mt-2 text-lg font-semibold">Mídias selecionadas</h2>
        </header>
        <div className="divide-y">
          {campaign.media.map((medium) => (
            <article className="flex items-center gap-3 p-4" key={medium.id}>
              <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-zinc-800 text-zinc-500">
                {medium.media_kind === "video" ? <Film size={17} /> : <ImageIcon size={17} />}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{medium.display_name}</p>
                <p className="mt-1 text-xs text-zinc-600">
                  {formatBytes(medium.size_bytes)} · {formatDuration(medium.duration_ms)}
                  {medium.width && medium.height ? ` · ${medium.width}×${medium.height}` : ""}
                </p>
                {medium.failure_reason && <p className="mt-1 text-xs text-red-300">{medium.failure_reason}</p>}
              </div>
              <StatusBadge status={medium.status} />
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
