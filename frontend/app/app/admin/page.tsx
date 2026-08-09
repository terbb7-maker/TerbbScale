"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Check,
  Crown,
  Database,
  Pencil,
  PauseCircle,
  RefreshCw,
  Search,
  ScrollText,
  Server,
  ShieldCheck,
  ShieldOff,
  Trash2,
  UserCheck,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";

type AdminUser = {
  id: string;
  email: string | null;
  full_name: string | null;
  status: string;
  is_platform_owner: boolean;
  timezone: string;
  approved_at: string | null;
  suspended_at: string | null;
  last_seen_at: string | null;
  created_at: string;
  roles: string[];
  connected_accounts: number;
  campaigns_count: number;
};
type Health = {
  status: string;
  database: { status: string };
  redis: { status: string };
  scheduler: { status: string; last_success_at?: string };
};
type Stats = {
  users: number;
  pending_users: number;
  connected_accounts: number;
  campaigns: number;
  publications: number;
  failed_publications: number;
};
type Plan = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  limits: Record<string, number>;
  active: boolean;
};
type AuditLog = {
  id: string;
  action: string;
  target_type: string;
  target_id: string | null;
  outcome: string;
  occurred_at: string;
};

export default function AdminPage() {
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const users = useQuery({ queryKey: ["admin-users"], queryFn: () => api<AdminUser[]>("/admin/users") });
  const profile = useQuery({ queryKey: ["admin-profile"], queryFn: () => api<{ is_platform_owner: boolean }>("/auth/me") });
  const health = useQuery({ queryKey: ["admin-health"], queryFn: () => api<Health>("/admin/health"), refetchInterval: 30_000 });
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: () => api<Stats>("/admin/stats") });
  const plans = useQuery({ queryKey: ["admin-plans"], queryFn: () => api<Plan[]>("/admin/plans") });
  const auditLogs = useQuery({ queryKey: ["admin-audit"], queryFn: () => api<AuditLog[]>("/admin/audit-logs?limit=20") });
  const decide = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api(`/admin/users/${id}/${action}`, { method: "POST", body: JSON.stringify({ reason: null }) }),
    onSuccess: () => {
      toast.success("Usuário atualizado.");
      client.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (error) => toast.error(error.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/admin/users/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success("Exclusão agendada conforme a retenção.");
      client.invalidateQueries({ queryKey: ["admin-users"] });
      client.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: (error) => toast.error(error.message),
  });
  const edit = useMutation({
    mutationFn: ({ id, full_name, timezone }: { id: string; full_name: string; timezone: string }) =>
      api(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify({ full_name, timezone }) }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["admin-users"] }),
    onError: (error) => toast.error(error.message),
  });
  const assignPlan = useMutation({
    mutationFn: ({ userId, planId }: { userId: string; planId: string }) =>
      api<void>(`/admin/users/${userId}/plan/${planId}`, { method: "PUT" }),
    onSuccess: () => toast.success("Plano atribuído."),
    onError: (error) => toast.error(error.message),
  });
  const setAdmin = useMutation({
    mutationFn: ({ id, isAdmin }: { id: string; isAdmin: boolean }) =>
      api(`/admin/users/${id}/admin`, { method: "PUT", body: JSON.stringify({ is_admin: isAdmin }) }),
    onSuccess: (_data, variables) => {
      toast.success(variables.isAdmin ? "Administrador liberado." : "Acesso administrativo removido.");
      client.invalidateQueries({ queryKey: ["admin-users"] });
      client.invalidateQueries({ queryKey: ["admin-audit"] });
    },
    onError: (error) => toast.error(error.message),
  });
  const filteredUsers = (users.data ?? []).filter((user) => {
    const term = search.trim().toLowerCase();
    const matchesSearch = !term || [user.email, user.full_name, ...user.roles].some((value) => value?.toLowerCase().includes(term));
    return matchesSearch && (statusFilter === "all" || user.status === statusFilter);
  });
  const canManageAdmins = profile.data?.is_platform_owner === true;
  const cards = [
    { label: "Banco", status: health.data?.database.status ?? "checking", icon: Database },
    { label: "Redis", status: health.data?.redis.status ?? "checking", icon: Server },
    { label: "Scheduler", status: health.data?.scheduler.status ?? "checking", icon: Activity },
    { label: "Usuários pendentes", status: String(stats.data?.pending_users ?? 0), icon: UserCheck },
  ];
  return (
    <>
      <PageHeader eyebrow="Administração" title="Controle da plataforma" description="Governança de usuários, permissões administrativas, planos e saúde operacional." actions={<button className="button-secondary" onClick={() => { users.refetch(); health.refetch(); profile.refetch(); }}><RefreshCw size={15} /> Atualizar</button>} />
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ label, status, icon: Icon }) => (
          <article className="panel p-5" key={label}><div className="flex items-center justify-between text-zinc-500"><span className="text-sm">{label}</span><Icon size={17} /></div><p className="mt-4 text-xl font-semibold capitalize">{status}</p></article>
        ))}
      </section>
      <section className="panel mt-4 overflow-hidden">
        <div className="border-b p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><h2 className="font-semibold">Usuários e acessos</h2><p className="mt-1 text-xs text-zinc-600">Aprovações, atividade, planos e privilégios por conta.</p></div>
            {canManageAdmins && <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs text-violet-300"><Crown size={14} /> Proprietário da plataforma</span>}
          </div>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <label className="relative min-w-0 flex-1"><Search className="pointer-events-none absolute left-3 top-2.5 text-zinc-600" size={15} /><input className="h-9 w-full rounded-lg border bg-zinc-950 pl-9 pr-3 text-sm outline-none focus:border-violet-500" placeholder="Buscar nome, e-mail ou papel…" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
            <select className="h-9 rounded-lg border bg-zinc-950 px-3 text-sm" aria-label="Filtrar por status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">Todos os status</option><option value="pending">Pendentes</option><option value="active">Ativos</option><option value="suspended">Suspensos</option><option value="rejected">Rejeitados</option></select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] text-left text-sm">
            <thead className="text-xs text-zinc-600"><tr><th className="px-5 py-3 font-medium">Usuário</th><th className="px-5 py-3 font-medium">Papel</th><th className="px-5 py-3 font-medium">Uso</th><th className="px-5 py-3 font-medium">Último acesso</th><th className="px-5 py-3 font-medium">Plano</th><th className="px-5 py-3 font-medium">Status</th><th className="px-5 py-3 font-medium" /></tr></thead>
            <tbody className="divide-y">
              {filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td className="px-5 py-4"><p className="font-medium">{user.full_name ?? "Sem nome"}</p><p className="mt-1 text-xs text-zinc-600">{user.email}</p></td>
                  <td className="px-5 py-4"><span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs ${user.is_platform_owner ? "bg-violet-500/15 text-violet-300" : user.roles.includes("admin") ? "bg-sky-500/15 text-sky-300" : "bg-zinc-800 text-zinc-400"}`}>{user.is_platform_owner ? <Crown size={13} /> : user.roles.includes("admin") ? <ShieldCheck size={13} /> : <Users size={13} />}{user.is_platform_owner ? "Dono" : user.roles.includes("admin") ? "Admin" : "Membro"}</span></td>
                  <td className="px-5 py-4 text-xs text-zinc-500"><span className="block">{user.connected_accounts} conta{user.connected_accounts === 1 ? "" : "s"}</span><span className="mt-1 block">{user.campaigns_count} campanha{user.campaigns_count === 1 ? "" : "s"}</span></td>
                  <td className="px-5 py-4 text-xs text-zinc-500">{user.last_seen_at ? new Date(user.last_seen_at).toLocaleString("pt-BR") : "Ainda não acessou"}</td>
                  <td className="px-5 py-4">
                    <select
                      aria-label={`Plano de ${user.email ?? user.id}`}
                      className="rounded-lg border bg-zinc-950 px-2 py-1.5 text-xs"
                      defaultValue=""
                      onChange={(event) => {
                        if (event.target.value) assignPlan.mutate({ userId: user.id, planId: event.target.value });
                      }}
                    >
                      <option value="">Atribuir…</option>
                      {(plans.data ?? []).filter((plan) => plan.active).map((plan) => <option value={plan.id} key={plan.id}>{plan.name}</option>)}
                    </select>
                  </td>
                  <td className="px-5 py-4"><StatusBadge status={user.status} /></td>
                  <td className="px-5 py-4">
                    <div className="flex justify-end gap-1">
                      {user.is_platform_owner ? <span title="Conta proprietária protegida" className="grid size-8 place-items-center text-violet-300"><Crown size={16} /></span> : <>
                        {canManageAdmins && <button title={user.roles.includes("admin") ? "Remover acesso administrativo" : "Tornar administrador"} className="grid size-8 place-items-center rounded-lg text-sky-300 hover:bg-sky-500/10" onClick={() => { const isAdmin = !user.roles.includes("admin"); if (window.confirm(isAdmin ? `Tornar ${user.email ?? "este usuário"} administrador?` : `Remover o acesso administrativo de ${user.email ?? "este usuário"}?`)) setAdmin.mutate({ id: user.id, isAdmin }); }}>{user.roles.includes("admin") ? <ShieldOff size={16} /> : <ShieldCheck size={16} />}</button>}
                        {user.status === "pending" && <><button title="Aprovar" className="grid size-8 place-items-center rounded-lg text-emerald-400 hover:bg-emerald-500/10" onClick={() => decide.mutate({ id: user.id, action: "approve" })}><Check size={16} /></button><button title="Rejeitar" className="grid size-8 place-items-center rounded-lg text-red-400 hover:bg-red-500/10" onClick={() => decide.mutate({ id: user.id, action: "reject" })}><X size={16} /></button></>}
                        {user.status === "active" && <button title="Suspender" className="grid size-8 place-items-center rounded-lg text-amber-400 hover:bg-amber-500/10" onClick={() => decide.mutate({ id: user.id, action: "suspend" })}><PauseCircle size={16} /></button>}
                        {["suspended", "rejected"].includes(user.status) && <button title="Reativar" className="grid size-8 place-items-center rounded-lg text-emerald-400 hover:bg-emerald-500/10" onClick={() => decide.mutate({ id: user.id, action: "reactivate" })}><UserCheck size={16} /></button>}
                        <button title="Editar" className="grid size-8 place-items-center rounded-lg text-zinc-400 hover:bg-zinc-800" onClick={() => { const fullName = window.prompt("Nome do usuário", user.full_name ?? ""); if (fullName === null) return; const timezone = window.prompt("Fuso horário", user.timezone); if (timezone) edit.mutate({ id: user.id, full_name: fullName, timezone }); }}><Pencil size={15} /></button>
                        <button title="Excluir" className="grid size-8 place-items-center rounded-lg text-red-400 hover:bg-red-500/10" onClick={() => { if (window.confirm("Excluir este usuário e cancelar suas operações?")) remove.mutate(user.id); }}><Trash2 size={15} /></button>
                      </>}
                    </div>
                  </td>
                </tr>
              ))}
              {!filteredUsers.length && <tr><td className="px-5 py-10 text-center text-sm text-zinc-600" colSpan={7}>Nenhum usuário encontrado com esses filtros.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
      <section className="mt-4 grid gap-4 xl:grid-cols-2">
        <article className="panel overflow-hidden">
          <div className="flex items-center gap-3 border-b p-5"><Activity size={17} className="text-violet-400" /><div><h2 className="font-semibold">Estatísticas globais</h2><p className="mt-1 text-xs text-zinc-600">Operação consolidada da plataforma</p></div></div>
          <div className="grid grid-cols-2 gap-px bg-zinc-800/70 sm:grid-cols-3">
            {[
              ["Usuários", stats.data?.users],
              ["Contas conectadas", stats.data?.connected_accounts],
              ["Campanhas", stats.data?.campaigns],
              ["Publicações", stats.data?.publications],
              ["Falhas", stats.data?.failed_publications],
              ["Pendentes", stats.data?.pending_users],
            ].map(([label, value]) => <div className="bg-[#101217] p-5" key={String(label)}><p className="text-2xl font-semibold">{value ?? 0}</p><p className="mt-1 text-xs text-zinc-600">{label}</p></div>)}
          </div>
        </article>
        <article className="panel overflow-hidden">
          <div className="flex items-center gap-3 border-b p-5"><Server size={17} className="text-violet-400" /><div><h2 className="font-semibold">Planos</h2><p className="mt-1 text-xs text-zinc-600">Limites disponíveis para atribuição</p></div></div>
          <div className="divide-y">
            {(plans.data ?? []).map((plan) => <div className="flex items-center justify-between p-5" key={plan.id}><div><p className="font-medium">{plan.name}</p><p className="mt-1 text-xs text-zinc-600">{plan.description}</p></div><StatusBadge status={plan.active ? "active" : "inactive"} /></div>)}
          </div>
        </article>
      </section>
      <section className="panel mt-4 overflow-hidden">
        <div className="flex items-center gap-3 border-b p-5"><ScrollText size={17} className="text-violet-400" /><div><h2 className="font-semibold">Auditoria recente</h2><p className="mt-1 text-xs text-zinc-600">Ações administrativas rastreáveis</p></div></div>
        <div className="divide-y">
          {(auditLogs.data ?? []).map((log) => <div className="flex items-center gap-4 px-5 py-3 text-sm" key={log.id}><span className="min-w-0 flex-1 truncate font-medium">{log.action}</span><span className="text-zinc-600">{log.target_type}</span><StatusBadge status={log.outcome} /><time className="text-xs text-zinc-600">{new Date(log.occurred_at).toLocaleString("pt-BR")}</time></div>)}
          {!auditLogs.data?.length && <p className="py-10 text-center text-sm text-zinc-600">Nenhuma ação administrativa registrada.</p>}
        </div>
      </section>
    </>
  );
}
