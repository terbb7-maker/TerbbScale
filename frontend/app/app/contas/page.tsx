"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Camera, Link2, MoreHorizontal, RefreshCw, ShieldAlert, Trash2 } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { toast } from "sonner";

import { AccountHealthDetails } from "@/components/account-health-details";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useAccountHealthEvents } from "@/hooks/use-account-health-events";
import { api } from "@/lib/api";
import type { Account } from "@/lib/types";

export default function AccountsPage() {
  const client = useQueryClient();
  useAccountHealthEvents();
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api<Account[]>("/accounts"), refetchInterval: 60_000 });
  const [selected, setSelected] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const connect = useMutation({
    mutationFn: () => api<{ authorization_url: string }>("/accounts/connect", { method: "POST" }),
    onSuccess: (data) => location.assign(data.authorization_url),
    onError: (error) => toast.error(error.message),
  });
  const refresh = useMutation({
    mutationFn: (id: string) => api<Account>(`/accounts/${id}/refresh-token`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Token atualizado.");
      client.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => toast.error(error.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/accounts/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success("Conta removida.");
      client.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => toast.error(error.message),
  });
  const bulkRemove = useMutation({
    mutationFn: (accountIds: string[]) => api<{ removed: number }>("/accounts/bulk-remove", {
      method: "POST",
      body: JSON.stringify({ account_ids: accountIds }),
    }),
    onSuccess: (result) => {
      toast.success(`${result.removed} conta${result.removed === 1 ? " removida" : "s removidas"}.`);
      setSelected([]);
      client.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => toast.error(error.message),
  });
  const checkHealth = useMutation({
    mutationFn: (id: string) => api<{ status: string }>(`/accounts/${id}/health-check`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Verificação iniciada.");
      client.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => toast.error(error.message),
  });
  const missingInsights = (accounts.data ?? []).filter(
    (account) => !account.granted_scopes.includes("instagram_business_manage_insights"),
  );
  const operational = (accounts.data ?? []).filter((account) => account.health_status === "operational").length;
  const attention = (accounts.data ?? []).filter((account) => ["reauth_required", "action_required", "permission_required", "temporarily_restricted", "possibly_suspended"].includes(account.health_status)).length;

  return (
    <>
      <PageHeader
        eyebrow="Instagram Login"
        title="Contas"
        description="Conecte e gerencie contas usando exclusivamente a autenticação oficial do Instagram."
        actions={
          <button className="button-primary" onClick={() => connect.mutate()} disabled={connect.isPending}>
            <Link2 size={16} /> Conectar Instagram
          </button>
        }
      />
      {!!missingInsights.length && (
        <section className="mb-4 flex flex-col gap-4 rounded-2xl border border-amber-500/25 bg-amber-500/5 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-medium text-amber-100">Autorize as métricas do Instagram</h2>
            <p className="mt-1 text-xs leading-5 text-amber-200/65">
              Reconecte a conta uma vez para liberar visualizações, curtidas, comentários, compartilhamentos e salvamentos.
            </p>
          </div>
          <button className="button-primary shrink-0" onClick={() => connect.mutate()} disabled={connect.isPending}>
            <RefreshCw size={15} /> Reconectar agora
          </button>
        </section>
      )}
      {!!accounts.data?.length && <section className="mb-4 grid gap-3 sm:grid-cols-3"><article className="panel p-4"><p className="text-xs text-zinc-600">Disponíveis para uso</p><p className="mt-2 text-2xl font-semibold text-emerald-400">{operational}</p></article><article className="panel p-4"><p className="text-xs text-zinc-600">Precisam de atenção</p><p className="mt-2 text-2xl font-semibold text-amber-400">{attention}</p></article><article className="panel p-4"><p className="text-xs text-zinc-600">Monitoramento</p><p className="mt-2 flex items-center gap-2 text-sm"><Activity size={16} className="text-violet-400" /> Ao vivo</p></article></section>}
      {!!selected.length && (
        <section className="mb-4 flex flex-col gap-3 rounded-2xl border border-violet-400/15 bg-violet-500/[0.06] p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm"><strong>{selected.length}</strong> conta{selected.length === 1 ? " selecionada" : "s selecionadas"}</p>
          <div className="flex gap-2"><button className="button-secondary" onClick={() => setSelected([])}>Cancelar</button><button className="button-danger" disabled={bulkRemove.isPending} onClick={() => confirm(`Remover ${selected.length} conta${selected.length === 1 ? "" : "s"}? As publicações futuras dessas contas serão canceladas.`) && bulkRemove.mutate(selected)}><Trash2 size={15} /> {bulkRemove.isPending ? "Removendo…" : "Remover selecionadas"}</button></div>
        </section>
      )}
      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b p-5">
          <div className="flex items-center gap-3">
            {!!accounts.data?.length && <input type="checkbox" aria-label="Selecionar todas as contas" checked={selected.length === accounts.data.length} onChange={() => setSelected(selected.length === accounts.data.length ? [] : accounts.data.map((item) => item.id))} />}
          <div>
            <h2 className="font-semibold">Contas conectadas</h2>
            <p className="mt-1 text-xs text-zinc-600">{accounts.data?.length ?? 0} contas nesta área de trabalho</p>
          </div></div>
          <button className="button-secondary px-3" onClick={() => accounts.refetch()}><RefreshCw size={15} /></button>
        </div>
        <div className="divide-y">
          {(accounts.data ?? []).map((account) => (
            <div key={account.id}>
            <article className="flex flex-col gap-4 p-5 md:flex-row md:items-center">
              <input type="checkbox" aria-label={`Selecionar @${account.username}`} checked={selected.includes(account.id)} onChange={() => setSelected(selected.includes(account.id) ? selected.filter((id) => id !== account.id) : [...selected, account.id])} />
              <div className="flex min-w-0 flex-1 items-center gap-4">
                {account.profile_picture_url ? (
                  <Image
                    className="size-11 rounded-full object-cover"
                    src={account.profile_picture_url}
                    alt=""
                    width={44}
                    height={44}
                    unoptimized
                  />
                ) : (
                  <span className="grid size-11 place-items-center rounded-full bg-violet-500/10 text-violet-400"><Camera size={19} /></span>
                )}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="truncate font-medium">{account.display_name ?? account.username}</h3>
                    <StatusBadge status={account.health_status} />
                  </div>
                  <p className="mt-1 truncate text-sm text-zinc-500">@{account.username} · {account.health_message ?? "Aguardando verificação"}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-7 text-sm md:flex">
                <div><p className="text-xs text-zinc-600">Publicações</p><p className="mt-1">{account.published_count}</p></div>
                <div><p className="text-xs text-zinc-600">Token expira</p><p className="mt-1">{account.token_expires_at ? new Date(account.token_expires_at).toLocaleDateString("pt-BR") : "—"}</p></div>
              </div>
              <div className="flex items-center gap-2">
                {!account.granted_scopes.includes("instagram_business_manage_insights") && (
                  <button className="button-secondary px-3 text-amber-300" title="Reconectar para liberar métricas" onClick={() => connect.mutate()} disabled={connect.isPending}><Link2 size={15} /></button>
                )}
                <button className="button-secondary px-3" title="Testar situação agora" onClick={() => checkHealth.mutate(account.id)} disabled={checkHealth.isPending && checkHealth.variables === account.id}>{account.health_status === "checking" ? <RefreshCw className="animate-spin" size={15} /> : <ShieldAlert size={15} />}</button>
                <button className="button-secondary px-3" title="Atualizar token" onClick={() => refresh.mutate(account.id)}><RefreshCw size={15} /></button>
                <button
                  className="button-secondary px-3 text-red-400"
                  title="Remover"
                  onClick={() => {
                    if (confirm(`Remover @${account.username}?`)) remove.mutate(account.id);
                  }}
                ><Trash2 size={15} /></button>
                <button className="button-secondary px-3" title="Ver situação e histórico" onClick={() => setExpanded(expanded === account.id ? null : account.id)}><MoreHorizontal size={15} /></button>
              </div>
            </article>
            {expanded === account.id && <AccountHealthDetails account={account} />}
            </div>
          ))}
          {!accounts.isLoading && !accounts.data?.length && (
            <div className="px-6 py-20 text-center">
              <span className="mx-auto grid size-12 place-items-center rounded-xl bg-zinc-800/60 text-zinc-500"><Camera size={22} /></span>
              <h3 className="mt-5 font-medium">Nenhuma conta conectada</h3>
              <p className="mt-2 text-sm text-zinc-600">Configure seu Instagram App e conecte a primeira conta.</p>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
