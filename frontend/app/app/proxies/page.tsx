"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit3, Network, Plus, RefreshCw, Trash2, Upload, Wifi } from "lucide-react";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { Proxy, ProxyImportResult, ProxyTestResult } from "@/lib/types";

type FormState = {
  name: string; protocol: Proxy["protocol"]; host: string; port: string; username: string;
  password: string; country: string; notes: string; is_active: boolean;
};

const emptyForm: FormState = {
  name: "", protocol: "http", host: "", port: "", username: "", password: "", country: "", notes: "", is_active: true,
};

export default function ProxiesPage() {
  const client = useQueryClient();
  const proxies = useQuery({ queryKey: ["proxies"], queryFn: () => api<Proxy[]>("/proxies") });
  const [form, setForm] = useState<FormState>(emptyForm);
  const [editing, setEditing] = useState<Proxy | null>(null);
  const [open, setOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importEntries, setImportEntries] = useState("");
  const [importProtocol, setImportProtocol] = useState<Proxy["protocol"]>("http");
  const [importCountry, setImportCountry] = useState("");
  const [importPrefix, setImportPrefix] = useState("Proxy");
  const [importErrors, setImportErrors] = useState<Array<{ line: number; error: string }>>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const refresh = () => client.invalidateQueries({ queryKey: ["proxies"] });
  const save = useMutation({
    mutationFn: () => api<Proxy>(editing ? `/proxies/${editing.id}` : "/proxies", {
      method: editing ? "PUT" : "POST",
      body: JSON.stringify({ ...form, port: Number(form.port), password: form.password || undefined }),
    }),
    onSuccess: () => { toast.success(editing ? "Proxy atualizado." : "Proxy cadastrado."); setOpen(false); setEditing(null); setForm(emptyForm); refresh(); },
    onError: (error) => toast.error(error.message),
  });
  const test = useMutation({
    mutationFn: (id: string) => api<ProxyTestResult>(`/proxies/${id}/test`, { method: "POST" }),
    onSuccess: (result) => { if (result.status === "online") toast.success("Proxy conectado com sucesso."); else toast.error(result.error ?? "Não foi possível conectar ao proxy."); refresh(); }, onError: (error) => toast.error(error.message),
  });
  const testAll = useMutation({
    mutationFn: () => api<{ tested: number; online: number; offline: number }>("/proxies/test-all", { method: "POST" }),
    onSuccess: (result) => { if (result.offline) toast.error(`${result.online} conectados e ${result.offline} com falha.`); else toast.success("Todos os proxies foram testados com sucesso."); refresh(); }, onError: (error) => toast.error(error.message),
  });
  const importProxies = useMutation({
    mutationFn: () => api<ProxyImportResult>("/proxies/import", { method: "POST", body: JSON.stringify({ entries: importEntries, protocol: importProtocol, country: importCountry || undefined, name_prefix: importPrefix || "Proxy" }) }),
    onSuccess: (result) => {
      setImportErrors(result.errors);
      if (result.created) { toast.success(`${result.created} proxy${result.created === 1 ? "" : "s"} importado${result.created === 1 ? "" : "s"}.`); setImportEntries(""); refresh(); }
      if (result.rejected) toast.error(`${result.rejected} linha${result.rejected === 1 ? "" : "s"} não pôde${result.rejected === 1 ? "" : "m"} ser importada${result.rejected === 1 ? "" : "s"}.`);
    },
    onError: (error) => toast.error(error.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/proxies/${id}`, { method: "DELETE" }),
    onSuccess: () => { toast.success("Proxy removido."); refresh(); }, onError: (error) => toast.error(error.message),
  });
  const bulkRemove = useMutation({
    mutationFn: (ids: string[]) => api<{ removed: number }>("/proxies/bulk-remove", {
      method: "POST",
      body: JSON.stringify({ proxy_ids: ids }),
    }),
    onSuccess: (result) => {
      toast.success(`${result.removed} proxy${result.removed === 1 ? " removida" : "s removidas"}.`);
      setSelectedIds([]);
      refresh();
    },
    onError: (error) => toast.error(error.message),
  });
  function edit(proxy: Proxy) {
    setEditing(proxy); setForm({ name: proxy.name, protocol: proxy.protocol, host: proxy.host, port: String(proxy.port), username: proxy.username ?? "", password: "", country: proxy.country ?? "", notes: proxy.notes ?? "", is_active: proxy.is_active }); setOpen(true);
  }
  function submit(event: FormEvent) { event.preventDefault(); save.mutate(); }
  return <>
    <PageHeader eyebrow="Conectividade" title="Proxies" description="Use proxies próprios por conta ou campanha, com teste de IP e latência." actions={<div className="flex flex-wrap gap-2"><button className="button-secondary" onClick={() => testAll.mutate()} disabled={testAll.isPending}><Wifi size={16} /> Testar todos</button><button className="button-secondary" onClick={() => { setImportErrors([]); setImportOpen(true); }}><Upload size={16} /> Importar lista</button><button className="button-primary" onClick={() => { setEditing(null); setForm(emptyForm); setOpen(true); }}><Plus size={16} /> Novo proxy</button></div>} />
    {importOpen && <section className="panel mb-4 p-5"><form className="grid gap-4 md:grid-cols-2" onSubmit={(event) => { event.preventDefault(); importProxies.mutate(); }}>
      <div className="md:col-span-2"><h2 className="font-semibold">Importar proxies</h2><p className="mt-1 text-sm text-zinc-500">Cole um proxy por linha, no formato <code>host:porta:usuário:senha</code>. Também funciona para importar uma única linha.</p></div>
      <label><span className="mb-2 block text-sm text-zinc-400">Tipo</span><select className="input" value={importProtocol} onChange={(e) => setImportProtocol(e.target.value as Proxy["protocol"])}><option value="http">HTTP</option><option value="https">HTTPS</option><option value="socks5">SOCKS5</option></select></label>
      <label><span className="mb-2 block text-sm text-zinc-400">País (opcional)</span><input className="input" value={importCountry} onChange={(e) => setImportCountry(e.target.value)} /></label>
      <label className="md:col-span-2"><span className="mb-2 block text-sm text-zinc-400">Prefixo do nome</span><input className="input" value={importPrefix} onChange={(e) => setImportPrefix(e.target.value)} /></label>
      <label className="md:col-span-2"><span className="mb-2 block text-sm text-zinc-400">Lista de proxies</span><textarea className="input min-h-52 font-mono text-xs" required placeholder="proxy39-br-hz.ipbr.pro:10000:usuario:senha" value={importEntries} onChange={(e) => setImportEntries(e.target.value)} /></label>
      {!!importErrors.length && <div className="md:col-span-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200"><p className="font-medium">Linhas não importadas</p><ul className="mt-1 list-inside list-disc">{importErrors.map((item) => <li key={item.line}>Linha {item.line}: {item.error}</li>)}</ul></div>}
      <div className="flex justify-end gap-2 md:col-span-2"><button type="button" className="button-secondary" onClick={() => setImportOpen(false)}>Fechar</button><button className="button-primary" disabled={importProxies.isPending}>{importProxies.isPending ? "Importando…" : "Importar proxies"}</button></div>
    </form></section>}
    {open && <section className="panel mb-4 p-5"><form className="grid gap-4 md:grid-cols-2" onSubmit={submit}>
      <label><span className="mb-2 block text-sm text-zinc-400">Nome</span><input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
      <label><span className="mb-2 block text-sm text-zinc-400">Tipo</span><select className="input" value={form.protocol} onChange={(e) => setForm({ ...form, protocol: e.target.value as Proxy["protocol"] })}><option value="http">HTTP</option><option value="https">HTTPS</option><option value="socks5">SOCKS5</option></select></label>
      <label><span className="mb-2 block text-sm text-zinc-400">Host</span><input className="input" required placeholder="proxy.exemplo.com" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} /></label>
      <label><span className="mb-2 block text-sm text-zinc-400">Porta</span><input className="input" required type="number" min="1" max="65535" value={form.port} onChange={(e) => setForm({ ...form, port: e.target.value })} /></label>
      <label><span className="mb-2 block text-sm text-zinc-400">Usuário</span><input className="input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></label>
      <label><span className="mb-2 block text-sm text-zinc-400">Senha {editing?.password_configured ? "(deixe vazia para manter)" : ""}</span><input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
      <label><span className="mb-2 block text-sm text-zinc-400">País</span><input className="input" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} /></label>
      <label className="md:col-span-2"><span className="mb-2 block text-sm text-zinc-400">Observações</span><textarea className="input min-h-20" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></label>
      <label className="flex items-center gap-2 text-sm text-zinc-400"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Ativo</label>
      <div className="flex justify-end gap-2"><button type="button" className="button-secondary" onClick={() => setOpen(false)}>Cancelar</button><button className="button-primary" disabled={save.isPending}>{save.isPending ? "Salvando…" : "Salvar proxy"}</button></div>
    </form></section>}
    {!!selectedIds.length && <section className="mb-4 flex flex-col gap-3 rounded-2xl border border-violet-400/15 bg-violet-500/[0.06] p-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm"><strong>{selectedIds.length}</strong> proxy{selectedIds.length === 1 ? " selecionada" : "s selecionadas"}</p><div className="flex gap-2"><button className="button-secondary" onClick={() => setSelectedIds([])}>Cancelar</button><button className="button-danger" disabled={bulkRemove.isPending} onClick={() => confirm(`Remover ${selectedIds.length} proxy${selectedIds.length === 1 ? "" : "s"}?`) && bulkRemove.mutate(selectedIds)}><Trash2 size={15} /> {bulkRemove.isPending ? "Removendo…" : "Remover selecionadas"}</button></div></section>}
    <section className="panel overflow-hidden"><div className="flex items-center justify-between border-b p-5"><div><h2 className="font-semibold">Proxies cadastrados</h2><p className="mt-1 text-xs text-zinc-600">{proxies.data?.length ?? 0} disponíveis neste workspace</p></div><button className="button-secondary px-3" onClick={() => proxies.refetch()}><RefreshCw size={15} /></button></div><div className="overflow-x-auto"><table className="w-full min-w-[1040px] text-left text-sm"><thead className="text-xs text-zinc-600"><tr><th className="px-5 py-3"><input aria-label="Selecionar todas as proxies" type="checkbox" checked={!!proxies.data?.length && selectedIds.length === proxies.data.length} onChange={() => setSelectedIds(selectedIds.length === proxies.data?.length ? [] : (proxies.data ?? []).map((item) => item.id))} /></th><th className="px-5 py-3">Nome</th><th className="px-5 py-3">País</th><th className="px-5 py-3">IP</th><th className="px-5 py-3">Porta</th><th className="px-5 py-3">Protocolo</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Latência</th><th className="px-5 py-3">Última verificação</th><th className="px-5 py-3">Contas</th><th className="px-5 py-3">Ações</th></tr></thead><tbody className="divide-y">{(proxies.data ?? []).map((proxy) => <tr className={selectedIds.includes(proxy.id) ? "bg-violet-500/[0.04]" : ""} key={proxy.id}><td className="px-5 py-4"><input aria-label={`Selecionar ${proxy.name}`} type="checkbox" checked={selectedIds.includes(proxy.id)} onChange={() => setSelectedIds(selectedIds.includes(proxy.id) ? selectedIds.filter((id) => id !== proxy.id) : [...selectedIds, proxy.id])} /></td><td className="px-5 py-4 font-medium">{proxy.name}</td><td className="px-5 py-4 text-zinc-400">{proxy.country ?? "—"}</td><td className="px-5 py-4 text-zinc-400">{proxy.public_ip ?? proxy.host}</td><td className="px-5 py-4 text-zinc-400">{proxy.port}</td><td className="px-5 py-4 uppercase text-zinc-400">{proxy.protocol}</td><td className="px-5 py-4"><StatusBadge status={proxy.is_active ? proxy.status : "inactive"} /></td><td className="px-5 py-4 text-zinc-400">{proxy.latency_ms === null ? "—" : `${proxy.latency_ms} ms`}</td><td className="px-5 py-4 text-zinc-400">{proxy.last_check ? new Date(proxy.last_check).toLocaleString("pt-BR") : "Nunca"}</td><td className="px-5 py-4 text-zinc-400">{proxy.accounts_using}</td><td className="px-5 py-4"><div className="flex gap-2"><button className="button-secondary px-2" title="Testar" onClick={() => test.mutate(proxy.id)}><Wifi size={14} /></button><button className="button-secondary px-2" title="Editar" onClick={() => edit(proxy)}><Edit3 size={14} /></button><button className="button-secondary px-2 text-red-400" title="Excluir" onClick={() => confirm(`Excluir ${proxy.name}?`) && remove.mutate(proxy.id)}><Trash2 size={14} /></button></div></td></tr>)}</tbody></table>{!proxies.isLoading && !proxies.data?.length && <div className="px-6 py-20 text-center text-zinc-600"><Network className="mx-auto" /><p className="mt-4 text-sm">Nenhum proxy cadastrado.</p></div>}</div></section>
  </>;
}
