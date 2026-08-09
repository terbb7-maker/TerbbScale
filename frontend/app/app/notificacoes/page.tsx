"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";

type Notification = { id: string; title: string; message: string; severity: string; read_at: string | null; created_at: string };

export default function NotificationsPage() {
  const client = useQueryClient();
  const notifications = useQuery({ queryKey: ["notifications"], queryFn: () => api<Notification[]>("/notifications") });
  const readAll = useMutation({
    mutationFn: () => api<void>("/notifications/read-all", { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["notifications"] }),
  });
  return (
    <>
      <PageHeader eyebrow="Central" title="Notificações" description="Conclusões de campanhas, falhas e eventos importantes da sua operação." actions={<button className="button-secondary" onClick={() => readAll.mutate()}><CheckCheck size={15} /> Marcar todas como lidas</button>} />
      <section className="panel divide-y">
        {(notifications.data ?? []).map((item) => (
          <article className={`flex gap-4 p-5 ${item.read_at ? "opacity-55" : ""}`} key={item.id}>
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-zinc-800 text-zinc-400"><Bell size={16} /></span>
            <div className="min-w-0 flex-1"><h2 className="text-sm font-medium">{item.title}</h2><p className="mt-1 text-sm text-zinc-500">{item.message}</p><p className="mt-2 text-[11px] text-zinc-700">{new Date(item.created_at).toLocaleString("pt-BR")}</p></div>
            {!item.read_at && <i className="mt-2 size-2 rounded-full bg-violet-400" />}
          </article>
        ))}
        {!notifications.isLoading && !notifications.data?.length && <p className="py-16 text-center text-sm text-zinc-600">Tudo tranquilo por aqui.</p>}
      </section>
    </>
  );
}
