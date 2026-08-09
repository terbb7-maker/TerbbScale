"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Save, ShieldCheck } from "lucide-react";
import { FormEvent } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";

type AppSettings = {
  instagram_app_id: string | null;
  app_secret_configured: boolean;
  app_secret_masked: string | null;
  redirect_uri: string | null;
  scopes: string[];
  timezone: string;
  notifications_enabled: boolean;
  app_verified: boolean;
  app_last_error: string | null;
};

export default function SettingsPage() {
  const client = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<AppSettings>("/settings") });
  const update = useMutation({
    mutationFn: (body: object) => api<AppSettings>("/settings/instagram-app", { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["settings"] });
      toast.success("Configurações protegidas e salvas.");
    },
    onError: (error) => toast.error(error.message),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    update.mutate({
      app_id: String(data.get("app_id")),
      app_secret: String(data.get("app_secret")) || null,
      redirect_uri: String(data.get("redirect_uri")),
      scopes: data.getAll("scopes"),
    });
  }
  const current = settings.data;
  const defaultRedirect =
    typeof window === "undefined"
      ? `${process.env.NEXT_PUBLIC_APP_URL ?? ""}/app/contas/callback`
      : `${window.location.origin}/app/contas/callback`;
  return (
    <>
      <PageHeader eyebrow="Workspace" title="Configurações" description="Cada usuário utiliza seu próprio Instagram App. Nenhuma credencial é compartilhada entre tenants." />
      <div className="grid gap-4 xl:grid-cols-[1fr_330px]">
        <form className="panel p-5 md:p-7" onSubmit={submit}>
          <div className="flex items-center gap-3 border-b pb-5">
            <span className="grid size-10 place-items-center rounded-xl bg-violet-500/10 text-violet-400"><KeyRound size={19} /></span>
            <div><h2 className="font-semibold">Instagram App</h2><p className="mt-1 text-xs text-zinc-600">Instagram Platform API com Instagram Login</p></div>
          </div>
          <div className="mt-6 grid gap-5">
            <label><span className="mb-2 block text-sm text-zinc-400">App ID</span><input className="input" name="app_id" defaultValue={current?.instagram_app_id ?? ""} required /></label>
            <label><span className="mb-2 block text-sm text-zinc-400">App Secret</span><input className="input" name="app_secret" type="password" placeholder={current?.app_secret_configured ? "Deixe vazio para manter o segredo atual" : "Informe o App Secret"} required={!current?.app_secret_configured} /></label>
            <label><span className="mb-2 block text-sm text-zinc-400">Redirect URI</span><input className="input" name="redirect_uri" type="url" defaultValue={current?.redirect_uri ?? defaultRedirect} required /></label>
            <fieldset>
              <legend className="mb-3 text-sm text-zinc-400">Scopes</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {[
                  { scope: "instagram_business_basic", label: "Perfil e informações básicas", required: true },
                  { scope: "instagram_business_content_publish", label: "Publicação de conteúdo", required: true },
                  { scope: "instagram_business_manage_insights", label: "Métricas e engajamento", required: true },
                  { scope: "instagram_business_manage_comments", label: "Gerenciar comentários", required: false },
                  { scope: "instagram_business_manage_messages", label: "Gerenciar mensagens", required: false },
                ].map(({ scope, label, required }) => (
                  <label className="flex gap-3 rounded-xl border p-3 text-sm" key={scope}>
                    <input
                      name="scopes"
                      type="checkbox"
                      value={scope}
                      defaultChecked={required || current?.scopes.includes(scope)}
                      onClick={required ? (event) => event.preventDefault() : undefined}
                      readOnly={Boolean(required)}
                    />
                    <span><span className="block text-zinc-300">{label} {required && <small className="text-violet-400">· obrigatório</small>}</span><span className="mt-1 block break-all text-[10px] text-zinc-600">{scope}</span></span>
                  </label>
                ))}
              </div>
            </fieldset>
            <button className="button-primary w-fit" disabled={update.isPending} type="submit"><Save size={16} /> Salvar credenciais</button>
          </div>
        </form>
        <aside className="space-y-4">
          <section className="panel p-5">
            <ShieldCheck className="text-emerald-400" size={22} />
            <h2 className="mt-4 font-semibold">Segredo criptografado</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-600">O App Secret é protegido com AES-256-GCM antes de chegar ao banco e nunca volta para o navegador.</p>
          </section>
          <section className="panel p-5">
            <p className="eyebrow">Status</p>
            <p className="mt-4 text-sm">{current?.app_secret_configured ? "App configurado" : "Configuração pendente"}</p>
            <p className="mt-2 text-xs text-zinc-600">{current?.app_last_error ?? "Nenhum erro recente."}</p>
          </section>
        </aside>
      </div>
    </>
  );
}
